import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
OptionalQueryStr = Annotated[str | None, Query()]
PayoutAmount = Annotated[float, Query(ge=0.0, le=1000000000.0)]
PaginationLimit = Annotated[int, Query(ge=1, le=100)]


class MoneyPrinterIdeaRequest(BaseModel):
    printer: str = Field(min_length=3, max_length=80)
    hypothesis: str = Field(min_length=10, max_length=500)
    expected_monthly_revenue_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    owner: str = Field(default='', max_length=80)


class MoneyPrinterValidationRequest(BaseModel):
    idea_id: int
    outcome: str = Field(default='validated', max_length=40)
    confidence: int = Field(default=70, ge=0, le=100)
    evidence: str = Field(default='', max_length=500)


class BankTransferRequest(BaseModel):
    to_tenant_id: str = Field(min_length=2, max_length=120)
    amount: float = Field(gt=0.0, le=1000000000.0)
    note: str = Field(default='', max_length=240)


class BankPayoutRequest(BaseModel):
    amount: float = Field(gt=0.0, le=1000000000.0)
    destination: str = Field(min_length=3, max_length=240)


@dataclass
class MoneyPrintersBankContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    money_printers: list[str]
    money_printer_ideas_memory: list[dict[str, Any]]
    money_printer_validations_memory: list[dict[str, Any]]
    bank_transactions_memory: list[dict[str, Any]]
    bank_payouts_memory: list[dict[str, Any]]
    normalize_printer_fn: Callable[[str], str]
    get_bank_account_fn: Callable[[str], dict[str, Any]]
    sync_settlements_fn: Callable[[str], list[dict[str, Any]]]
    bank_balance_fn: Callable[[str], float]
    record_bank_tx_fn: Callable[[str, str, float, str, dict[str, Any]], dict[str, Any]]
    tenant_display_name_fn: Callable[[str], str]
    append_credit_fn: Callable[[str, int, str], None]
    append_notification_fn: Callable[[str, str, str, str], None]
    append_audit_fn: Callable[[str, str, dict[str, Any]], None]
    idea_not_found: str
    invalid_outcome: str
    insufficient_balance: str
    insufficient_payout_balance: str


def register_money_printers_bank_routes(*, router: APIRouter, context: MoneyPrintersBankContext) -> None:
    _register_portfolio_rollup_route(router, context)
    _register_ideas_crud_routes(router, context)
    _register_backlog_route(router, context)
    _register_bank_routes(router, context)


def _register_portfolio_rollup_route(router: APIRouter, ctx: MoneyPrintersBankContext) -> None:
    @router.get('/money-printers/portfolio')
    def money_printers_portfolio(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:money-printers:portfolio', 240, 60)
        with ctx.lock:
            ideas = [item.copy() for item in ctx.money_printer_ideas_memory if item.get('tenant_id') == auth.tenant_id]
            validations = [
                item.copy()
                for item in ctx.money_printer_validations_memory
                if item.get('tenant_id') == auth.tenant_id
            ]
        rollup, _ = _build_printer_rollup(ctx.money_printers, ideas, validations)
        readiness_score = min(
            100,
            int(sum(item['validated'] for item in rollup.values()) * 8)
            + int(sum(item['ideas'] for item in rollup.values()) * 2),
        )
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'money_printers': {
                'readiness_score': readiness_score,
                'portfolio': [rollup[p] for p in ctx.money_printers],
            },
        }


def _build_printer_rollup(
    money_printers: list[str],
    ideas: list[dict[str, Any]],
    validations: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[int]]]:
    rollup: dict[str, dict[str, Any]] = {
        printer: {'printer': printer, 'ideas': 0, 'validated': 0, 'invalidated': 0,
                  'avg_confidence': 0, 'projected_monthly_revenue_usd': 0.0}
        for printer in money_printers
    }
    confidences: dict[str, list[int]] = {printer: [] for printer in money_printers}
    for idea in ideas:
        printer = str(idea.get('printer'))
        if printer not in rollup:
            continue
        rollup[printer]['ideas'] += 1
        rollup[printer]['projected_monthly_revenue_usd'] += float(idea.get('expected_monthly_revenue_usd', 0.0))
    for validation in validations:
        printer = str(validation.get('printer'))
        if printer not in rollup:
            continue
        outcome = str(validation.get('outcome', ''))
        if outcome == 'validated':
            rollup[printer]['validated'] += 1
        elif outcome == 'invalidated':
            rollup[printer]['invalidated'] += 1
        confidences[printer].append(int(validation.get('confidence', 0)))
    for printer in money_printers:
        scores = confidences[printer]
        if scores:
            rollup[printer]['avg_confidence'] = int(sum(scores) / len(scores))
        rollup[printer]['projected_monthly_revenue_usd'] = round(
            float(rollup[printer]['projected_monthly_revenue_usd']), 2
        )
    return rollup, confidences


def _register_ideas_crud_routes(router: APIRouter, ctx: MoneyPrintersBankContext) -> None:
    @router.post('/money-printers/ideas')
    def create_money_printer_idea(payload: MoneyPrinterIdeaRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:money-printers:ideas:create', 120, 60)
        with ctx.lock:
            now_iso = datetime.now(UTC).isoformat()
            printer = ctx.normalize_printer_fn(payload.printer)
            idea: dict[str, Any] = {
                'id': len(ctx.money_printer_ideas_memory) + 1,
                'tenant_id': auth.tenant_id,
                'printer': printer,
                'hypothesis': payload.hypothesis,
                'expected_monthly_revenue_usd': round(float(payload.expected_monthly_revenue_usd), 2),
                'owner': payload.owner.strip() or ctx.tenant_display_name_fn(auth.tenant_id),
                'status': 'open',
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            ctx.money_printer_ideas_memory.append(idea)
            ctx.append_audit_fn(auth.tenant_id, 'money_printer_idea_created', {'idea_id': idea['id'], 'printer': printer})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'idea': idea}

    @router.post(
        '/money-printers/ideas/validate',
        responses={
            404: {'description': 'Money printer idea not found.'},
            422: {'description': 'Invalid validation outcome.'},
        },
    )
    def validate_money_printer_idea(payload: MoneyPrinterValidationRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:money-printers:ideas:validate', 120, 60)
        with ctx.lock:
            idea = next(
                (
                    item for item in ctx.money_printer_ideas_memory
                    if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == int(payload.idea_id)
                ),
                None,
            )
            if idea is None:
                raise HTTPException(status_code=404, detail=ctx.idea_not_found)
            outcome = str(payload.outcome).strip().lower()
            if outcome not in ('validated', 'invalidated', 'inconclusive'):
                raise HTTPException(status_code=422, detail=ctx.invalid_outcome)
            now_iso = datetime.now(UTC).isoformat()
            validation: dict[str, Any] = {
                'id': len(ctx.money_printer_validations_memory) + 1,
                'tenant_id': auth.tenant_id,
                'idea_id': int(idea['id']),
                'printer': str(idea.get('printer')),
                'outcome': outcome,
                'confidence': int(payload.confidence),
                'evidence': payload.evidence,
                'created_at': now_iso,
            }
            ctx.money_printer_validations_memory.append(validation)
            idea['status'] = outcome
            idea['updated_at'] = now_iso
            credits_awarded = 0
            if outcome == 'validated':
                credits_awarded = 40
                ctx.append_credit_fn(auth.tenant_id, credits_awarded, 'money_printer_validation_success')
                ctx.append_notification_fn(
                    auth.tenant_id,
                    'Money Printer Hypothesis Validated',
                    f"Idea #{idea['id']} for {idea['printer']} validated at {payload.confidence}% confidence.",
                    'money_printers',
                )
            ctx.append_audit_fn(
                auth.tenant_id,
                'money_printer_idea_validated',
                {'idea_id': idea['id'], 'outcome': outcome, 'confidence': int(payload.confidence)},
            )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'validation': validation, 'credits_awarded': credits_awarded}


def _register_backlog_route(router: APIRouter, ctx: MoneyPrintersBankContext) -> None:
    @router.get('/money-printers/backlog')
    def money_printers_backlog(auth: AuthDep, printer: OptionalQueryStr = None, status: OptionalQueryStr = None, limit: PaginationLimit = 25) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:money-printers:backlog', 240, 60)
        with ctx.lock:
            ideas = [item.copy() for item in ctx.money_printer_ideas_memory if item.get('tenant_id') == auth.tenant_id]
        if printer:
            printer_filter = ctx.normalize_printer_fn(printer)
            ideas = [item for item in ideas if str(item.get('printer')) == printer_filter]
        if status:
            status_filter = status.strip().lower()
            ideas = [item for item in ideas if str(item.get('status', '')).lower() == status_filter]
        ideas.sort(key=lambda item: str(item.get('updated_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(ideas), 'ideas': ideas[:limit]}


def _register_bank_routes(router: APIRouter, ctx: MoneyPrintersBankContext) -> None:
    from datetime import UTC, datetime

    @router.get('/money-printers/nuxtron-bank/wallet')
    def nuxtron_bank_wallet(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-bank:wallet', 240, 60)
        with ctx.lock:
            account = ctx.get_bank_account_fn(auth.tenant_id)
            new_settlements = ctx.sync_settlements_fn(auth.tenant_id)
            balance = ctx.bank_balance_fn(auth.tenant_id)
            recent = [item.copy() for item in ctx.bank_transactions_memory if item.get('tenant_id') == auth.tenant_id]
        recent.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'wallet': {
                'account': account,
                'available_balance_usd': balance,
                'new_settlements': len(new_settlements),
                'recent_transactions': recent[:20],
            },
        }

    @router.post('/money-printers/nuxtron-bank/transfer', responses={422: {'description': 'Insufficient bank wallet balance.'}})
    def nuxtron_bank_transfer(payload: BankTransferRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-bank:transfer', 120, 60)
        with ctx.lock:
            ctx.get_bank_account_fn(auth.tenant_id)
            ctx.get_bank_account_fn(payload.to_tenant_id)
            ctx.sync_settlements_fn(auth.tenant_id)
            fee = round(float(payload.amount) * 0.01, 2)
            total_debit = round(float(payload.amount) + fee, 2)
            balance = ctx.bank_balance_fn(auth.tenant_id)
            if balance < total_debit:
                raise HTTPException(status_code=422, detail=ctx.insufficient_balance)
            debit_tx = ctx.record_bank_tx_fn(
                auth.tenant_id, 'debit', total_debit, 'transfer_out',
                {'to_tenant_id': payload.to_tenant_id, 'amount': round(float(payload.amount), 2), 'fee': fee, 'note': payload.note},
            )
            credit_tx = ctx.record_bank_tx_fn(
                payload.to_tenant_id, 'credit', float(payload.amount), 'transfer_in',
                {'from_tenant_id': auth.tenant_id, 'note': payload.note},
            )
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_bank_transfer_out',
                {'debit_tx_id': debit_tx['id'], 'to_tenant_id': payload.to_tenant_id, 'amount': payload.amount})
            ctx.append_audit_fn(payload.to_tenant_id, 'nuxtron_bank_transfer_in',
                {'credit_tx_id': credit_tx['id'], 'from_tenant_id': auth.tenant_id, 'amount': payload.amount})
        return {
            'status': 'ok', 'tenant_id': auth.tenant_id,
            'transfer': {'amount': round(float(payload.amount), 2), 'fee': fee, 'total_debit': total_debit, 'to_tenant_id': payload.to_tenant_id},
            'debit_transaction': debit_tx,
        }

    @router.get('/money-printers/nuxtron-bank/payout-preview')
    def nuxtron_bank_payout_preview(auth: AuthDep, amount: PayoutAmount = 0.0) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-bank:payout-preview', 240, 60)
        with ctx.lock:
            ctx.get_bank_account_fn(auth.tenant_id)
            ctx.sync_settlements_fn(auth.tenant_id)
            balance = ctx.bank_balance_fn(auth.tenant_id)
        payout_fee = round(float(amount) * 0.015, 2)
        net = round(max(0.0, float(amount) - payout_fee), 2)
        total_debit = round(float(amount), 2)
        return {
            'status': 'ok', 'tenant_id': auth.tenant_id,
            'payout_preview': {
                'requested_amount_usd': total_debit, 'payout_fee_usd': payout_fee,
                'net_payout_usd': net, 'available_balance_usd': balance, 'can_payout': balance >= total_debit,
            },
        }

    @router.post('/money-printers/nuxtron-bank/payouts', responses={422: {'description': 'Insufficient balance for payout request.'}})
    def nuxtron_bank_request_payout(payload: BankPayoutRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-bank:payouts:create', 60, 60)
        with ctx.lock:
            ctx.get_bank_account_fn(auth.tenant_id)
            ctx.sync_settlements_fn(auth.tenant_id)
            balance = ctx.bank_balance_fn(auth.tenant_id)
            amount = round(float(payload.amount), 2)
            if balance < amount:
                raise HTTPException(status_code=422, detail=ctx.insufficient_payout_balance)
            payout_fee = round(amount * 0.015, 2)
            payout: dict[str, Any] = {
                'id': len(ctx.bank_payouts_memory) + 1,
                'tenant_id': auth.tenant_id,
                'amount_usd': amount,
                'payout_fee_usd': payout_fee,
                'net_payout_usd': round(amount - payout_fee, 2),
                'destination': payload.destination,
                'status': 'queued',
                'created_at': datetime.now(UTC).isoformat(),
            }
            ctx.bank_payouts_memory.append(payout)
            debit_tx = ctx.record_bank_tx_fn(
                auth.tenant_id, 'debit', amount, 'payout_request',
                {'payout_id': payout['id'], 'destination': payload.destination},
            )
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_bank_payout_requested', {'payout_id': payout['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'payout': payout, 'debit_transaction': debit_tx}

    @router.get('/money-printers/nuxtron-bank/payouts')
    def nuxtron_bank_list_payouts(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-bank:payouts:list', 240, 60)
        with ctx.lock:
            payouts = [item.copy() for item in ctx.bank_payouts_memory if item.get('tenant_id') == auth.tenant_id]
        payouts.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(payouts), 'payouts': payouts[:100]}
