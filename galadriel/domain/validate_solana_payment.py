from dataclasses import dataclass
from typing import List
from typing import Optional
from typing import Set

from solana.rpc.api import Client
from solders.pubkey import Pubkey  # pylint: disable=E0401
from solders.signature import Signature  # pylint: disable=E0401

from galadriel.entities import Message
from galadriel.entities import Pricing
from galadriel.errors import PaymentValidationError


@dataclass
class TaskAndPaymentSignature:
    task: str
    signature: str


@dataclass
class TaskAndPaymentSignatureResponse(TaskAndPaymentSignature):
    amount_transferred_lamport: int


def execute(pricing: Pricing, existing_payments: Set[str], request: Message) -> TaskAndPaymentSignatureResponse:
    """Validate the payment for the request.
    Args:
        pricing: Pricing configuration, containing the wallet address and payment amount required
        existing_payments: Already validated payments to avoid duplications
        request: The message containing the transaction signature
    Returns:
        The task to be executed
    Raises:
        PaymentValidationError: If the payment validation fails
    """
    task_and_payment = _extract_transaction_signature(request.content)
    if not task_and_payment:
        raise PaymentValidationError(
            "No transaction signature found in the message. Please include your payment transaction signature."
        )
    if task_and_payment.signature in existing_payments:
        raise PaymentValidationError(
            f"Transaction {task_and_payment.signature} has already been used. Please submit a new payment."
        )
    sol_transferred_lamport = _get_sol_amount_transferred(pricing, task_and_payment.signature)
    if sol_transferred_lamport < pricing.cost * 10**9:
        raise PaymentValidationError(
            f"Payment validation failed for transaction {task_and_payment.signature}. "
            f"Please ensure you've sent {pricing.cost} SOL to {pricing.wallet_address}"
        )
    existing_payments.add(task_and_payment.signature)
    return TaskAndPaymentSignatureResponse(
        task=task_and_payment.task,
        signature=task_and_payment.signature,
        amount_transferred_lamport=sol_transferred_lamport,
    )


def _get_sol_amount_transferred(pricing: Pricing, tx_signature: str) -> int:
    http_client = Client("https://api.mainnet-beta.solana.com")
    tx_sig = Signature.from_string(tx_signature)
    tx_info = http_client.get_transaction(tx_sig=tx_sig, max_supported_transaction_version=10)
    if not tx_info.value:
        return False
    transaction = tx_info.value.transaction.transaction  # The actual transaction
    account_keys = transaction.message.account_keys  # type: ignore
    index = _get_key_index(account_keys, pricing.wallet_address)  # type: ignore
    if index < 0:
        return False

    meta = tx_info.value.transaction.meta
    if meta.err is not None:  # type: ignore
        return False

    pre_balance = meta.pre_balances[index]  # type: ignore
    post_balance = meta.post_balances[index]  # type: ignore
    amount_sent = post_balance - pre_balance
    return amount_sent


def _get_key_index(account_keys: List[Pubkey], wallet_address: str) -> int:
    """
    Returns the index of the wallet address
    :param account_keys:
    :param wallet_address:
    :return: non-zero number if present, -1 otherwise
    """
    wallet_key = Pubkey.from_string(wallet_address)
    for i, key in enumerate(account_keys):
        if wallet_key == key:
            return i
    return -1


def _extract_transaction_signature(message: str) -> Optional[TaskAndPaymentSignature]:
    """
    Given a string parses it to the task and the payment
    For example: "How long should I hold my ETH portfolio before selling?
    https://solscan.io/tx/5aqB4BGzQyFybjvKBjdcP8KAstZo81ooUZnf64vSbLLWbUqNSGgXWaGHNteiK2EJrjTmDKdLYHamJpdQBFevWuvy"

    :param message: string
    :return: TaskAndPaymentSignature if valid, none otherwise
    """
    if not message:
        return None

    if "https://solscan.io/tx/" in message:
        task, payment = message.split("https://solscan.io/tx/")
        task = task.strip()
        payment_signature = payment.replace("https://solscan.io/tx/", "").strip()
        return TaskAndPaymentSignature(
            task=task,
            signature=payment_signature,
        )

    signature = _find_signature(message)
    if signature:
        task = message.replace(signature, "").strip()
        return TaskAndPaymentSignature(task=task, signature=signature)
    return None


def _find_signature(message: str) -> Optional[str]:
    for word in message.split():
        try:
            signature = Signature.from_string(word.strip())
            return str(signature)
        except Exception:
            pass
    return None
