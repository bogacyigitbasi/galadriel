import asyncio
import base64
import json

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed, Confirmed
from solana.rpc.types import TxOpts
from solders import message
from solders.keypair import Keypair  # pylint: disable=E0401
from solders.pubkey import Pubkey  # pylint: disable=E0401
from solders.transaction import VersionedTransaction  # pylint: disable=E0401

from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID

from jupiter_python_sdk.jupiter import Jupiter

from galadriel.tools.web3.wallet_tool import WalletTool


# API endpoints for Jupiter Protocol
SOLANA_API_URL = "https://api.mainnet-beta.solana.com"
JUPITER_QUOTE_API_URL = "https://quote-api.jup.ag/v6/quote?"
JUPITER_SWAP_API_URL = "https://quote-api.jup.ag/v6/swap"
JUPITER_OPEN_ORDER_API_URL = "https://jup.ag/api/limit/v1/createOrder"
JUPITER_CANCEL_ORDERS_API_URL = "https://jup.ag/api/limit/v1/cancelOrders"
JUPITER_QUERY_OPEN_ORDERS_API_URL = "https://jup.ag/api/limit/v1/openOrders?wallet="
JUPITER_QUERY_ORDER_HISTORY_API_URL = "https://jup.ag/api/limit/v1/orderHistory"
JUPITER_QUERY_TRADE_HISTORY_API_URL = "https://jup.ag/api/limit/v1/tradeHistory"


class SwapTokenTool(WalletTool):
    """Tool for performing token swaps using Jupiter Protocol on Solana.

    This tool enables token swaps between any two SPL tokens using Jupiter's
    aggregator for optimal routing and pricing.

    Attributes:
        name (str): Tool identifier for the agent system
        description (str): Description of the tool's functionality
        inputs (dict): Schema for the required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "swap_token"
    description = "Swaps one token for another in the user's portfolio."
    inputs = {
        "user_address": {
            "type": "string",
            "description": "The solana address of the user",
        },
        "token1": {"type": "string", "description": "The address of the token to sell"},
        "token2": {"type": "string", "description": "The address of the token to buy"},
        "amount": {"type": "number", "description": "The amount of token1 to swap"},
    }
    output_type = "string"

    def forward(self, user_address: str, token1: str, token2: str, amount: float) -> str:  # pylint: disable=W0221
        """Execute a token swap transaction.

        Args:
            user_address (str): The Solana address of the user
            token1 (str): The address of the token to sell
            token2 (str): The address of the token to buy
            amount (float): The amount of token1 to swap

        Returns:
            str: A success message containing the transaction signature

        Note:
            Uses asyncio to run the swap operation in an event loop
        """
        wallet = self.wallet_repository.get_wallet()

        result = asyncio.run(swap(wallet, user_address, token1, float(token2), int(amount)))

        return f"Successfully swapped {amount} {token1} for {token2}, tx sig: {result}."


# pylint: disable=R0914
async def swap(
    wallet: Keypair,
    output_mint: str,
    input_mint: str,
    input_amount: float,
    slippage_bps: int = 300,
) -> str:
    """Execute a token swap using Jupiter Protocol.

    Performs a swap between two tokens using Jupiter's aggregator for optimal
    routing and pricing. Handles transaction construction, signing, and confirmation.

    Args:
        wallet (Keypair): The signer wallet for the transaction
        output_mint (str): Target token mint address
        input_mint (str): Source token mint address
        input_amount (float): Amount of input token to swap
        slippage_bps (int, optional): Slippage tolerance in basis points. Defaults to 300 (3%)

    Returns:
        str: The transaction signature

    Raises:
        Exception: If the swap fails for any reason

    Note:
        - Connects to Solana mainnet via RPC
        - Uses Jupiter's quote API for price discovery
        - Handles token decimal conversion
        - Confirms transaction completion
        - Prints transaction URLs for monitoring
    """
    # Initialize clients
    async_client = AsyncClient(SOLANA_API_URL)
    jupiter = Jupiter(
        async_client=async_client,
        keypair=wallet,
        quote_api_url=JUPITER_QUOTE_API_URL,
        swap_api_url=JUPITER_SWAP_API_URL,
        open_order_api_url=JUPITER_OPEN_ORDER_API_URL,
        cancel_orders_api_url=JUPITER_CANCEL_ORDERS_API_URL,
        query_open_orders_api_url=JUPITER_QUERY_OPEN_ORDERS_API_URL,
        query_order_history_api_url=JUPITER_QUERY_ORDER_HISTORY_API_URL,
        query_trade_history_api_url=JUPITER_QUERY_TRADE_HISTORY_API_URL,
    )

    # Convert addresses to strings
    input_mint = str(input_mint)
    output_mint = str(output_mint)

    # Get token decimals and adjust amount
    spl_client = AsyncToken(async_client, Pubkey.from_string(input_mint), TOKEN_PROGRAM_ID, wallet)
    mint = await spl_client.get_mint_info()
    decimals = mint.decimals
    input_amount = int(input_amount * 10**decimals)

    try:
        # Get swap transaction data
        transaction_data = await jupiter.swap(
            input_mint,
            output_mint,
            input_amount,
            only_direct_routes=False,
            slippage_bps=slippage_bps,
        )

        # Construct and sign transaction
        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
        signature = wallet.sign_message(message.to_bytes_versioned(raw_transaction.message))
        signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])

        # Send and confirm transaction
        opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
        result = await async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        print(f"Transaction sent: {json.loads(result.to_json())}")
        transaction_id = json.loads(result.to_json())["result"]
        print(f"Transaction sent: https://explorer.solana.com/tx/{transaction_id}")
        await async_client.confirm_transaction(signature, commitment=Confirmed)
        print(f"Transaction confirmed: https://explorer.solana.com/tx/{transaction_id}")
        return str(signature)

    except Exception as e:
        raise Exception(f"Swap failed: {str(e)}")  # pylint: disable=W0719
