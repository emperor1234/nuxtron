"""
Lindy.ai Email Management API Router

Endpoints for email management, OAuth, AI drafting, and analytics.
Production-grade with full error handling and security.
"""

import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import AuthDep, get_db
from ..models_lindy_email import Email, EmailDraft, EmailOAuthCredential
from ..services_lindy_email import (
    DraftGenerationRequest,
    EmailManagementService,
    EmailSyncRequest,
    OAuthCallbackRequest,
    SendDraftRequest,
    encrypt_credential,
)

router = APIRouter(prefix='/api/email', tags=['Email Management'])


# ==================== OAuth Integration ====================

@router.post('/oauth/initialize/{provider}')
def initialize_oauth(
    provider: str,
    auth: AuthDep,
    db: Session = Depends(get_db),
) -> dict:
    """
    Initialize OAuth flow for email provider.
    
    Returns OAuth URL for user to authorize.
    """
    
    if provider not in ['gmail', 'outlook']:
        raise HTTPException(status_code=400, detail='Invalid provider')
    
    state = str(uuid.uuid4())
    
    if provider == 'gmail':
        oauth_url = (
            'https://accounts.google.com/o/oauth2/v2/auth?'
            f'client_id={os.getenv("GMAIL_CLIENT_ID")}&'
            f'redirect_uri={os.getenv("GMAIL_REDIRECT_URI")}&'
            'scope=https://www.googleapis.com/auth/gmail.readonly%20'
            'https://www.googleapis.com/auth/gmail.modify&'
            'response_type=code&'
            f'state={state}&'
            'access_type=offline'
        )
    
    elif provider == 'outlook':
        oauth_url = (
            'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?'
            f'client_id={os.getenv("OUTLOOK_CLIENT_ID")}&'
            f'redirect_uri={os.getenv("OUTLOOK_REDIRECT_URI")}&'
            'scope=Mail.Read%20Mail.ReadWrite%20offline_access&'
            'response_type=code&'
            f'state={state}'
        )
    
    # Store state in Redis for validation
    import redis
    r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379)
    r.setex(f'oauth_state:{state}', 600, f'{auth.tenant_id}:{provider}')
    
    return {
        'success': True,
        'oauth_url': oauth_url,
        'state': state,
    }


@router.post('/oauth/callback')
async def handle_oauth_callback(
    request: OAuthCallbackRequest,
    auth: AuthDep,
    db: Session = Depends(get_db),
) -> dict:
    """
    Handle OAuth callback from provider.
    
    Exchanges authorization code for access token.
    """
    
    # Validate state
    import redis
    r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379)
    state_value = r.get(f'oauth_state:{request.state}')
    
    if not state_value:
        raise HTTPException(status_code=400, detail='Invalid or expired state')
    
    stored_tenant, stored_provider = state_value.decode().split(':')
    if stored_tenant != auth.tenant_id or stored_provider != request.provider:
        raise HTTPException(status_code=400, detail='State mismatch')
    
    # Exchange code for token
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            if request.provider == 'gmail':
                token_url = 'https://oauth2.googleapis.com/token'
                data = {
                    'code': request.code,
                    'client_id': os.getenv('GMAIL_CLIENT_ID'),
                    'client_secret': os.getenv('GMAIL_CLIENT_SECRET'),
                    'redirect_uri': os.getenv('GMAIL_REDIRECT_URI'),
                    'grant_type': 'authorization_code',
                }
                
            elif request.provider == 'outlook':
                token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
                data = {
                    'code': request.code,
                    'client_id': os.getenv('OUTLOOK_CLIENT_ID'),
                    'client_secret': os.getenv('OUTLOOK_CLIENT_SECRET'),
                    'redirect_uri': os.getenv('OUTLOOK_REDIRECT_URI'),
                    'grant_type': 'authorization_code',
                    'scope': 'Mail.Read Mail.ReadWrite offline_access',
                }
            
            async with session.post(token_url, data=data) as resp:
                token_data = await resp.json()
        
        if 'error' in token_data:
            raise HTTPException(status_code=400, detail=token_data.get('error_description', 'OAuth error'))
        
        # Extract email address
        access_token = token_data['access_token']
        
        if request.provider == 'gmail':
            # Get email from Gmail API
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                ) as resp:
                    userinfo = await resp.json()
                    user_email = userinfo.get('email', 'unknown@gmail.com')
        
        elif request.provider == 'outlook':
            # Get email from Microsoft Graph
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://graph.microsoft.com/v1.0/me',
                    headers={'Authorization': f'Bearer {access_token}'}
                ) as resp:
                    userinfo = await resp.json()
                    user_email = userinfo.get('userPrincipalName', 'unknown@outlook.com')
        
        # Store encrypted credentials
        refresh_token = token_data.get('refresh_token')
        token_data.get('expires_in')
        
        # Check if credential already exists
        existing = db.query(EmailOAuthCredential).filter(
            EmailOAuthCredential.tenant_id == auth.tenant_id,
            EmailOAuthCredential.email_provider == request.provider,
        ).first()
        
        if existing:
            # Update existing credential
            existing.access_token_encrypted = encrypt_credential(access_token)
            if refresh_token:
                existing.refresh_token_encrypted = encrypt_credential(refresh_token)
            existing.user_email = user_email
            db.commit()
        else:
            # Create new credential
            credential = EmailOAuthCredential(
                tenant_id=auth.tenant_id,
                email_provider=request.provider,
                user_email=user_email,
                access_token_encrypted=encrypt_credential(access_token),
                refresh_token_encrypted=encrypt_credential(refresh_token) if refresh_token else None,
                scopes=['mail.read', 'mail.write'],
                is_active=True,
            )
            db.add(credential)
            db.commit()
        
        # Clean up state
        r.delete(f'oauth_state:{request.state}')
        
        return {
            'success': True,
            'provider': request.provider,
            'user_email': user_email,
            'message': 'OAuth connected successfully',
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'OAuth error: {str(e)}')


# ==================== Email Sync ====================

@router.post('/sync')
async def sync_emails(
    request: EmailSyncRequest,
    auth: AuthDep,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """
    Sync emails from provider.
    
    Can be run in background for large syncs.
    """
    
    service = EmailManagementService(db)
    
    # Run sync
    result = await service.sync_emails(
        tenant_id=auth.tenant_id,
        provider=request.provider,
        force_full=request.force_full_sync,
        limit=request.limit,
    )
    
    return result


@router.get('/inbox')
def get_inbox(
    auth: AuthDep,
    status: str = Query('unread', pattern='^(unread|read|archived|all)$'),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """Get emails from inbox."""
    
    query = db.query(Email).filter(Email.tenant_id == auth.tenant_id)
    
    if status != 'all':
        query = query.filter(Email.status == status)
    
    total = query.count()
    emails = query.order_by(Email.email_received_at.desc()).offset(offset).limit(limit).all()
    
    return {
        'success': True,
        'total': total,
        'emails': [
            {
                'id': e.id,
                'from': e.from_address,
                'to': e.to_addresses,
                'subject': e.subject,
                'body_preview': e.body[:100] if e.body else '',
                'priority': e.priority,
                'ai_labels': e.ai_labels,
                'requires_response': e.requires_response,
                'received_at': e.email_received_at.isoformat(),
                'sentiment': e.sentiment,
            }
            for e in emails
        ],
        'limit': limit,
        'offset': offset,
    }


@router.get('/email/{email_id}')
def get_email(
    email_id: int,
    auth: AuthDep,
    db: Session = Depends(get_db),
) -> dict:
    """Get full email details."""
    
    email = db.query(Email).filter(
        Email.id == email_id,
        Email.tenant_id == auth.tenant_id,
    ).first()
    
    if not email:
        raise HTTPException(status_code=404, detail='Email not found')
    
    return {
        'success': True,
        'email': {
            'id': email.id,
            'from': email.from_address,
            'to': email.to_addresses,
            'cc': email.cc_addresses,
            'subject': email.subject,
            'body': email.body,
            'body_html': email.body_html,
            'priority': email.priority,
            'ai_labels': email.ai_labels,
            'requires_response': email.requires_response,
            'sentiment': email.sentiment,
            'received_at': email.email_received_at.isoformat(),
            'thread_id': email.thread_id,
            'has_attachments': email.has_attachments,
        },
    }


# ==================== Draft Generation ====================

@router.post('/draft/generate')
async def generate_draft(
    request: DraftGenerationRequest,
    auth: AuthDep,
    db: Session = Depends(get_db),
) -> dict:
    """Generate an AI-powered email draft."""
    
    service = EmailManagementService(db)
    
    result = await service.generate_draft(request, auth.tenant_id)
    
    if result.get('success'):
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get('error'))


@router.get('/drafts')
def list_drafts(
    auth: AuthDep,
    status: str = Query('draft', pattern='^(draft|sent|all)$'),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """List AI-generated drafts."""
    
    query = db.query(EmailDraft).filter(EmailDraft.tenant_id == auth.tenant_id)
    
    if status != 'all':
        query = query.filter(EmailDraft.status == status)
    
    total = query.count()
    drafts = query.order_by(EmailDraft.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        'success': True,
        'total': total,
        'drafts': [
            {
                'id': d.id,
                'subject': d.subject,
                'to': d.to_addresses,
                'preview': d.draft_text[:100],
                'tone': d.tone,
                'status': d.status,
                'confidence': d.ai_confidence,
                'created_at': d.created_at.isoformat(),
            }
            for d in drafts
        ],
    }


@router.get('/draft/{draft_id}')
def get_draft(
    draft_id: int,
    auth: AuthDep,
    db: Session = Depends(get_db),
) -> dict:
    """Get full draft details."""
    
    draft = db.query(EmailDraft).filter(
        EmailDraft.id == draft_id,
        EmailDraft.tenant_id == auth.tenant_id,
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail='Draft not found')
    
    return {
        'success': True,
        'draft': {
            'id': draft.id,
            'subject': draft.subject,
            'to': draft.to_addresses,
            'cc': draft.cc_addresses,
            'body': draft.draft_text,
            'tone': draft.tone,
            'status': draft.status,
            'confidence': draft.ai_confidence,
            'model': draft.model_used,
            'created_at': draft.created_at.isoformat(),
        },
    }


@router.post('/draft/{draft_id}/send')
async def send_draft(
    draft_id: int,
    request: SendDraftRequest,
    auth: AuthDep,
    db: Session = Depends(get_db),
) -> dict:
    """Send an AI-generated draft."""
    
    service = EmailManagementService(db)
    
    result = await service.send_draft(
        draft_id=draft_id,
        from_email=request.from_email,
        provider=request.provider,
        tenant_id=auth.tenant_id,
    )
    
    if result.get('success'):
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get('error'))


@router.post('/draft/{draft_id}/regenerate')
async def regenerate_draft(
    draft_id: int,
    auth: AuthDep,
    tone: str = Query('professional', pattern='^(professional|casual|assertive|friendly)$'),
    db: Session = Depends(get_db),
) -> dict:
    """Regenerate a draft with different tone."""
    
    draft = db.query(EmailDraft).filter(
        EmailDraft.id == draft_id,
        EmailDraft.tenant_id == auth.tenant_id,
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail='Draft not found')
    
    # Get original email if replying
    if draft.original_email_id:
        original = db.query(Email).filter(Email.id == draft.original_email_id).first()
        if not original:
            raise HTTPException(status_code=404, detail='Original email not found')
        
        service = EmailManagementService(db)
        request = DraftGenerationRequest(
            email_id=draft.original_email_id,
            to_addresses=draft.to_addresses,
            subject=draft.subject,
            tone=tone,
        )
    else:
        service = EmailManagementService(db)
        request = DraftGenerationRequest(
            to_addresses=draft.to_addresses,
            subject=draft.subject,
            tone=tone,
        )
    
    result = await service.generate_draft(request, auth.tenant_id)
    
    return result


# ==================== Analytics ====================

@router.get('/analytics')
def get_email_analytics(
    auth: AuthDep,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
) -> dict:
    """Get email analytics."""
    
    from datetime import datetime, timedelta

    from sqlalchemy import func
    
    start_date = (datetime.now() - timedelta(days=days)).date()
    
    total_emails = db.query(func.count(Email.id)).filter(
        Email.tenant_id == auth.tenant_id,
        Email.email_received_at >= start_date,
    ).scalar()
    
    unread_count = db.query(func.count(Email.id)).filter(
        Email.tenant_id == auth.tenant_id,
        Email.status == 'unread',
    ).scalar()
    
    urgent_count = db.query(func.count(Email.id)).filter(
        Email.tenant_id == auth.tenant_id,
        Email.priority == 'urgent',
    ).scalar()
    
    requires_response_count = db.query(func.count(Email.id)).filter(
        Email.tenant_id == auth.tenant_id,
        Email.requires_response,
    ).scalar()
    
    drafts_generated = db.query(func.count(EmailDraft.id)).filter(
        EmailDraft.tenant_id == auth.tenant_id,
        EmailDraft.created_at >= start_date,
    ).scalar()
    
    return {
        'success': True,
        'analytics': {
            'total_emails': total_emails,
            'unread_count': unread_count,
            'urgent_count': urgent_count,
            'requires_response': requires_response_count,
            'ai_drafts_generated': drafts_generated,
            'period_days': days,
        },
    }


# ==================== Status ====================

@router.get('/status')
def get_email_status(
    auth: AuthDep,
    db: Session = Depends(get_db),
) -> dict:
    """Get email system status."""
    
    credentials = db.query(EmailOAuthCredential).filter(
        EmailOAuthCredential.tenant_id == auth.tenant_id,
        EmailOAuthCredential.is_active,
    ).all()
    
    return {
        'success': True,
        'status': {
            'connected_providers': [
                {
                    'provider': c.email_provider,
                    'email': c.user_email,
                    'last_synced': c.last_synced_at.isoformat() if c.last_synced_at else None,
                }
                for c in credentials
            ],
            'total_emails': db.query(Email).filter(
                Email.tenant_id == auth.tenant_id
            ).count(),
            'total_drafts': db.query(EmailDraft).filter(
                EmailDraft.tenant_id == auth.tenant_id
            ).count(),
        },
    }


# ==================== Exports ====================

__all__ = [
    'router',
]
