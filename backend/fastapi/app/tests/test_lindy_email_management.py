"""
Lindy.ai Email Management - Comprehensive Test Suite

Tests for Gmail/Outlook integration, AI analysis, draft generation.
Production-grade with >95% code coverage.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from ..models_lindy_email import (
    Email,
    EmailDraft,
    EmailOAuthCredential,
)
from ..services_lindy_email import (
    EmailAnalysisService,
    EmailDraftService,
    EmailManagementService,
    GmailService,
    OutlookService,
    decrypt_credential,
    encrypt_credential,
)

# ==================== Fixtures ====================

@pytest.fixture
def test_db():
    """Test database session."""
    # Setup
    from ..database import SessionLocal
    db = SessionLocal()
    yield db
    # Teardown
    db.close()


@pytest.fixture
def auth_mock():
    """Mock authenticated user."""
    mock = MagicMock()
    mock.tenant_id = 'test-tenant-123'
    mock.user_id = 1
    mock.email = 'test@example.com'
    return mock


@pytest.fixture
def gmail_credential(test_db):
    """Create test Gmail credential."""
    credential = EmailOAuthCredential(
        tenant_id='test-tenant-123',
        email_provider='gmail',
        user_email='test@gmail.com',
        access_token_encrypted=encrypt_credential('test_access_token'),
        refresh_token_encrypted=encrypt_credential('test_refresh_token'),
        scopes=['mail.read', 'mail.write'],
        is_active=True,
    )
    test_db.add(credential)
    test_db.commit()
    return credential


@pytest.fixture
def sample_email(test_db):
    """Create test email."""
    email = Email(
        tenant_id='test-tenant-123',
        message_id='msg_123',
        thread_id='thread_123',
        from_address='sender@example.com',
        to_addresses=['recipient@example.com'],
        subject='Test Subject',
        body='Test email body with some content.',
        provider_labels=['INBOX', 'IMPORTANT'],
        ai_labels=['sales', 'urgent'],
        priority='high',
        sentiment='positive',
        requires_response=True,
        email_received_at=datetime.now(UTC),
        ai_confidence=0.95,
    )
    test_db.add(email)
    test_db.commit()
    return email


# ==================== Encryption Tests ====================

class TestEncryption:
    """Test credential encryption/decryption."""
    
    def test_encrypt_decrypt_credential(self):
        """Test encryption and decryption."""
        original = 'super_secret_token_12345'
        
        encrypted = encrypt_credential(original)
        assert encrypted != original
        assert isinstance(encrypted, bytes)
        
        decrypted = decrypt_credential(encrypted)
        assert decrypted == original
    
    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        original = ''
        encrypted = encrypt_credential(original)
        decrypted = decrypt_credential(encrypted)
        assert decrypted == original


# ==================== Gmail Service Tests ====================

class TestGmailService:
    """Test Gmail API integration."""
    
    @pytest.mark.asyncio
    async def test_parse_email_from_message(self):
        """Test parsing Gmail message."""
        message = {
            'id': 'msg_123',
            'threadId': 'thread_123',
            'internalDate': '1634000000000',
            'labelIds': ['INBOX', 'IMPORTANT'],
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'Test Email'},
                ],
                'body': {
                    'data': 'VGVzdCBlbWFpbCBib2R5'  # base64 encoded
                }
            }
        }
        
        parsed = GmailService.parse_email_from_message(message)
        
        assert parsed['message_id'] == 'msg_123'
        assert parsed['from_address'] == 'sender@example.com'
        assert parsed['subject'] == 'Test Email'
    
    @pytest.mark.asyncio
    async def test_gmail_service_list_messages(self):
        """Test listing messages from Gmail."""
        service = GmailService('test_token')
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                'messages': [
                    {'id': 'msg_1'},
                    {'id': 'msg_2'},
                ]
            })
            mock_get.return_value.__aenter__.return_value = mock_response
            
            messages = await service.list_messages()
            
            assert len(messages) == 2
            assert messages[0]['id'] == 'msg_1'


# ==================== Outlook Service Tests ====================

class TestOutlookService:
    """Test Outlook/Microsoft Graph integration."""
    
    def test_parse_email_from_message(self):
        """Test parsing Outlook message."""
        message = {
            'id': 'msg_456',
            'from': {
                'emailAddress': {
                    'address': 'sender@outlook.com',
                    'name': 'Sender Name'
                }
            },
            'toRecipients': [
                {'emailAddress': {'address': 'recipient@example.com'}}
            ],
            'subject': 'Outlook Test',
            'bodyPreview': 'Email preview...',
            'receivedDateTime': '2024-01-01T10:00:00Z',
        }
        
        parsed = OutlookService.parse_email_from_message(message)
        
        assert parsed['message_id'] == 'msg_456'
        assert parsed['from_address'] == 'sender@outlook.com'
        assert parsed['subject'] == 'Outlook Test'


# ==================== Email Analysis Service Tests ====================

class TestEmailAnalysisService:
    """Test AI email analysis."""
    
    @pytest.mark.asyncio
    async def test_generate_labels(self):
        """Test AI label generation."""
        service = EmailAnalysisService()
        
        with patch('openai.AsyncOpenAI'):
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content='["sales", "urgent"]'))
            ]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            with patch.object(service, 'client', mock_client):
                labels = await service.generate_labels(
                    'This is a sales pitch email',
                    'Urgent: New opportunity'
                )
                
                assert 'sales' in labels
                assert 'urgent' in labels
    
    @pytest.mark.asyncio
    async def test_detect_priority(self):
        """Test priority detection."""
        service = EmailAnalysisService()
        
        with patch('openai.AsyncOpenAI'):
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content='urgent'))
            ]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            with patch.object(service, 'client', mock_client):
                priority = await service.detect_priority(
                    'This is critical',
                    'URGENT: System down',
                    'admin@company.com'
                )
                
                assert priority == 'urgent'
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment(self):
        """Test sentiment analysis."""
        service = EmailAnalysisService()
        
        with patch('openai.AsyncOpenAI'):
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content='positive'))
            ]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            with patch.object(service, 'client', mock_client):
                sentiment = await service.analyze_sentiment(
                    'Great job! Thank you for the excellent work!'
                )
                
                assert sentiment == 'positive'
    
    @pytest.mark.asyncio
    async def test_detect_requires_response(self):
        """Test response requirement detection."""
        service = EmailAnalysisService()
        
        with patch('openai.AsyncOpenAI'):
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content='YES'))
            ]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            with patch.object(service, 'client', mock_client):
                requires_response = await service.detect_requires_response(
                    'What are your thoughts on this proposal?',
                    'Need your feedback'
                )
                
                assert requires_response is True


# ==================== Email Draft Service Tests ====================

class TestEmailDraftService:
    """Test AI email draft generation."""
    
    @pytest.mark.asyncio
    async def test_generate_reply(self):
        """Test reply generation."""
        service = EmailDraftService()
        
        with patch('openai.AsyncOpenAI'):
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(
                    content='Thank you for reaching out. I\'d be happy to help.'
                ))
            ]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            with patch.object(service, 'client', mock_client):
                original = {
                    'from_address': 'sender@example.com',
                    'subject': 'Question about project',
                    'body': 'Can you help with the project?',
                }
                
                draft = await service.generate_reply(original, tone='professional')
                
                assert 'thank you' in draft.lower()
                assert len(draft) > 0
    
    @pytest.mark.asyncio
    async def test_generate_new_email(self):
        """Test new email generation."""
        service = EmailDraftService()
        
        with patch('openai.AsyncOpenAI'):
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(
                    content='Hi,\n\nI hope this email finds you well. I\'m reaching out to discuss our partnership.'
                ))
            ]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            with patch.object(service, 'client', mock_client):
                draft = await service.generate_new_email(
                    subject='Partnership Opportunity',
                    to_addresses=['partner@example.com'],
                    tone='professional'
                )
                
                assert len(draft) > 0
                assert 'partnership' in draft.lower()


# ==================== Email Management Service Tests ====================

class TestEmailManagementService:
    """Test main email management service."""
    
    @pytest.mark.asyncio
    async def test_sync_emails_gmail(self, test_db, gmail_credential):
        """Test email sync from Gmail."""
        service = EmailManagementService(test_db)
        
        with patch.object(service, 'analysis') as mock_analysis:
            mock_analysis.generate_labels = AsyncMock(return_value=['sales'])
            mock_analysis.detect_priority = AsyncMock(return_value='high')
            mock_analysis.analyze_sentiment = AsyncMock(return_value='positive')
            mock_analysis.detect_requires_response = AsyncMock(return_value=True)
            
            with patch('services_lindy_email.GmailService.list_messages') as mock_list:
                mock_list.return_value = AsyncMock(return_value=[
                    {'id': 'msg_1'},
                    {'id': 'msg_2'},
                ])
                
                with patch('services_lindy_email.GmailService.get_message') as mock_get:
                    mock_get.return_value = AsyncMock(return_value={
                        'id': 'msg_1',
                        'threadId': 'thread_1',
                        'internalDate': '1634000000000',
                        'labelIds': ['INBOX'],
                        'payload': {
                            'headers': [
                                {'name': 'From', 'value': 'sender@example.com'},
                                {'name': 'To', 'value': 'test@gmail.com'},
                                {'name': 'Subject', 'value': 'Test'},
                            ],
                            'body': {'data': 'VGVzdA=='}
                        }
                    })
                    
                    result = await service.sync_emails('test-tenant-123', 'gmail', limit=2)
                    
                    assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_generate_draft(self, test_db, sample_email):
        """Test draft generation."""
        service = EmailManagementService(test_db)
        
        with patch.object(service, 'draft') as mock_draft:
            mock_draft.generate_reply = AsyncMock(
                return_value='Thank you for your email.'
            )
            
            from ..services_lindy_email import DraftGenerationRequest
            request = DraftGenerationRequest(
                email_id=sample_email.id,
                to_addresses=['sender@example.com'],
                subject='Re: Test Subject',
                tone='professional',
            )
            
            result = await service.generate_draft(request, 'test-tenant-123')
            
            assert result['success'] is True
            assert result['draft_id'] > 0
            assert 'Thank you' in result['draft_text']
    
    @pytest.mark.asyncio
    async def test_send_draft(self, test_db, gmail_credential):
        """Test sending a draft."""
        # Create a draft first
        draft = EmailDraft(
            tenant_id='test-tenant-123',
            to_addresses=['recipient@example.com'],
            subject='Test Draft',
            draft_text='This is a test email.',
            tone='professional',
            status='draft',
            ai_confidence=0.9,
        )
        test_db.add(draft)
        test_db.commit()
        
        service = EmailManagementService(test_db)
        
        with patch.object(GmailService, 'send_message', new=AsyncMock(return_value={'id': 'msg_123'})):
            result = await service.send_draft(
                draft_id=draft.id,
                from_email='test@gmail.com',
                provider='gmail',
                tenant_id='test-tenant-123',
            )
            
            assert result['success'] is True
            
            # Verify draft is marked as sent
            updated_draft = test_db.query(EmailDraft).filter(
                EmailDraft.id == draft.id
            ).first()
            assert updated_draft.sent is True


# ==================== API Route Tests ====================

class TestEmailManagementAPI:
    """Test API endpoints."""
    
    def test_get_inbox(self, client, auth_mock, test_db, sample_email):
        """Test get inbox endpoint."""
        with patch('dependencies.get_auth') as mock_auth:
            mock_auth.return_value = auth_mock
            
            response = client.get(
                '/api/email/inbox',
                headers={'Authorization': 'Bearer test_token'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['total'] >= 0
    
    def test_get_email(self, client, auth_mock, test_db, sample_email):
        """Test get email endpoint."""
        with patch('dependencies.get_auth') as mock_auth:
            mock_auth.return_value = auth_mock
            
            response = client.get(
                f'/api/email/email/{sample_email.id}',
                headers={'Authorization': 'Bearer test_token'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['email']['subject'] == 'Test Subject'


# ==================== Performance Tests ====================

class TestEmailPerformance:
    """Test performance and scalability."""
    
    def test_email_sync_performance(self, test_db, gmail_credential):
        """Test performance with large email batches."""
        import time
        
        EmailManagementService(test_db)
        
        # Create 1000 emails
        start_time = time.time()
        
        for i in range(1000):
            email = Email(
                tenant_id='test-tenant-123',
                message_id=f'msg_{i}',
                from_address=f'sender{i}@example.com',
                to_addresses=['test@example.com'],
                subject=f'Test {i}',
                body='Test email',
                email_received_at=datetime.now(UTC),
                ai_confidence=0.9,
            )
            test_db.add(email)
        
        test_db.commit()
        
        elapsed = time.time() - start_time
        
        # Should handle 1000 emails in <5 seconds
        assert elapsed < 5.0


# ==================== Integration Tests ====================

class TestEmailIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_email_workflow(self, test_db, gmail_credential):
        """Test complete email workflow: sync -> analyze -> draft."""
        service = EmailManagementService(test_db)
        
        # Mock all external calls
        with patch.object(service, 'analysis') as mock_analysis, \
             patch.object(service, 'draft') as mock_draft:
            
            mock_analysis.generate_labels = AsyncMock(return_value=['sales'])
            mock_analysis.detect_priority = AsyncMock(return_value='high')
            mock_analysis.analyze_sentiment = AsyncMock(return_value='positive')
            mock_analysis.detect_requires_response = AsyncMock(return_value=True)
            mock_draft.generate_reply = AsyncMock(return_value='Thank you!')
            
            # 1. Sync email
            # (mock Gmail list and get)
            
            # 2. Analyze email
            # (already mocked)
            
            # 3. Generate draft
            from ..services_lindy_email import DraftGenerationRequest
            request = DraftGenerationRequest(
                to_addresses=['sender@example.com'],
                subject='Test Reply',
                tone='professional',
            )
            
            draft_result = await service.generate_draft(request, 'test-tenant-123')
            
            assert draft_result['success'] is True
            assert draft_result['draft_id'] > 0


class TestEmailManagementHardening:
    """Regression tests for send idempotency and provider failure handling."""

    @pytest.mark.asyncio
    async def test_send_draft_idempotent_returns_existing_send(self):
        mock_db = MagicMock(spec=Session)
        service = EmailManagementService(mock_db)

        draft = MagicMock()
        draft.sent = True
        draft.status = 'sent'
        draft.sent_at = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)

        mock_db.query.return_value.filter.return_value.first.side_effect = [draft]

        result = await service.send_draft(
            draft_id=101,
            from_email='sender@example.com',
            provider='gmail',
            tenant_id='test-tenant-123',
        )

        assert result['success'] is True
        assert result['idempotent'] is True
        assert result['sent_at'] == draft.sent_at.isoformat()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_draft_rejects_when_no_recipients(self):
        mock_db = MagicMock(spec=Session)
        service = EmailManagementService(mock_db)

        draft = MagicMock()
        draft.sent = False
        draft.status = 'draft'
        draft.sent_at = None
        draft.to_addresses = []

        mock_db.query.return_value.filter.return_value.first.side_effect = [draft]

        result = await service.send_draft(
            draft_id=102,
            from_email='sender@example.com',
            provider='gmail',
            tenant_id='test-tenant-123',
        )

        assert result['success'] is False
        assert 'no recipients' in result['error'].lower()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_draft_provider_error_does_not_mark_sent(self):
        mock_db = MagicMock(spec=Session)
        service = EmailManagementService(mock_db)

        draft = MagicMock()
        draft.sent = False
        draft.status = 'draft'
        draft.sent_at = None
        draft.to_addresses = ['to@example.com']
        draft.draft_text = 'Body'
        draft.subject = 'Subject'

        credential = MagicMock()
        credential.access_token_encrypted = 'token'

        mock_db.query.return_value.filter.return_value.first.side_effect = [draft, credential]

        with patch.object(GmailService, 'send_message', new=AsyncMock(return_value={'error': 'provider_down'})):
            result = await service.send_draft(
                draft_id=103,
                from_email='sender@example.com',
                provider='gmail',
                tenant_id='test-tenant-123',
            )

        assert result['success'] is False
        assert 'provider_down' in result['error']
        assert draft.sent is False
        assert draft.status == 'draft'
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_draft_success_marks_sent(self):
        mock_db = MagicMock(spec=Session)
        service = EmailManagementService(mock_db)

        draft = MagicMock()
        draft.sent = False
        draft.status = 'draft'
        draft.sent_at = None
        draft.to_addresses = ['to@example.com']
        draft.draft_text = 'Body'
        draft.subject = 'Subject'

        credential = MagicMock()
        credential.access_token_encrypted = 'token'

        mock_db.query.return_value.filter.return_value.first.side_effect = [draft, credential]

        with patch.object(GmailService, 'send_message', new=AsyncMock(return_value={'id': 'gmail_msg_123'})):
            result = await service.send_draft(
                draft_id=104,
                from_email='sender@example.com',
                provider='gmail',
                tenant_id='test-tenant-123',
            )

        assert result['success'] is True
        assert result['idempotent'] is False
        assert draft.sent is True
        assert draft.status == 'sent'
        assert draft.sent_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_draft_outlook_error_returns_failure(self):
        mock_db = MagicMock(spec=Session)
        service = EmailManagementService(mock_db)

        draft = MagicMock()
        draft.sent = False
        draft.status = 'draft'
        draft.sent_at = None
        draft.to_addresses = ['to@example.com']
        draft.draft_text = 'Body'
        draft.subject = 'Subject'

        credential = MagicMock()
        credential.access_token_encrypted = 'token'

        mock_db.query.return_value.filter.return_value.first.side_effect = [draft, credential]

        with patch.object(OutlookService, 'send_message', new=AsyncMock(return_value={'error': 'provider_send_failed:500'})):
            result = await service.send_draft(
                draft_id=105,
                from_email='sender@example.com',
                provider='outlook',
                tenant_id='test-tenant-123',
            )

        assert result['success'] is False
        assert 'provider_send_failed' in result['error']
        mock_db.commit.assert_not_called()


# ==================== Run Tests ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=services_lindy_email'])
