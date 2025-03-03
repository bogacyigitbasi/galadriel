import os
import requests

from galadriel.core_agent import Tool


class CoingeckoTool(Tool):
    """Base class for Coingecko API tools.

    This class provides common functionality for accessing the Coingecko API,
    including API key management and authentication.

    Required Environment Variables:
        COINGECKO_API_KEY: Your Coingecko API key for authentication

    For more information about Coingecko API, see:
    https://www.coingecko.com/api/documentation
    """

    def __init__(self, *args, **kwargs):
        """Initialize the Coingecko tool.

        Args:
            *args: Variable length argument list passed to parent Tool class
            **kwargs: Arbitrary keyword arguments passed to parent Tool class

        Raises:
            ValueError: If COINGECKO_API_KEY environment variable is not set
        """
        self.api_key = os.getenv("COINGECKO_API_KEY")
        if not self.api_key:
            raise ValueError("COINGECKO_API_KEY environment variable is not set")
        super().__init__(*args, **kwargs)


class GetCoinPriceTool(CoingeckoTool):
    """Tool for retrieving current cryptocurrency price and market data.

    Fetches current price, market cap, 24hr volume, and 24hr price change
    for a specified cryptocurrency.

    Attributes:
        name (str): Tool identifier for the agent system
        description (str): Description of the tool's functionality
        inputs (dict): Schema for the required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "get_coin_price"
    description = "This is a tool that returns the price of given crypto token together with market cap, 24hr vol and 24hr change."  # pylint: disable=C0301
    inputs = {
        "task": {
            "type": "string",
            "description": "The full name of the token. For example 'solana' not 'sol'",
        }
    }
    output_type = "string"

    def forward(self, task: str) -> str:  # pylint: disable=W0221
        """Fetch current price and market data for a cryptocurrency.

        Args:
            task (str): The full name of the cryptocurrency (e.g., 'bitcoin')

        Returns:
            str: JSON string containing price and market data

        Note:
            Returns data including:
            - Current price in USD
            - Market capitalization
            - 24-hour trading volume
            - 24-hour price change percentage
            - Last updated timestamp
        """
        response = call_coingecko_api(
            api_key=self.api_key,
            request="https://api.coingecko.com/api/v3/simple/price"
            "?vs_currencies=usd"
            "&include_market_cap=true"
            "&include_24hr_vol=true"
            "&include_24hr_change=true"
            "&include_last_updated_at=true"
            "&precision=2"
            "&ids=" + task,
        )
        data = response.json()
        return data


class GetCoinHistoricalDataTool(CoingeckoTool):
    """Tool for retrieving historical cryptocurrency price data.

    Fetches historical price data for a specified cryptocurrency over
    a given time period.

    Attributes:
        name (str): Tool identifier for the agent system
        description (str): Description of the tool's functionality
        inputs (dict): Schema for the required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "get_coin_historical_data"
    description = "This is a tool that returns the historical data of given crypto token."
    inputs = {
        "task": {
            "type": "string",
            "description": "The full name of the token. For example 'solana' not 'sol'",
        },
        "days": {
            "type": "string",
            "description": "Data up to number of days ago, you may use any integer for number of days",
        },
    }
    output_type = "string"

    def forward(self, task: str, days: str) -> str:  # pylint: disable=W0221
        """Fetch historical price data for a cryptocurrency.

        Args:
            task (str): The full name of the cryptocurrency (e.g., 'bitcoin')
            days (str): Number of days of historical data to retrieve

        Returns:
            str: JSON string containing historical price data

        Note:
            Returns time series data including prices, market caps, and volumes
        """
        response = call_coingecko_api(
            api_key=self.api_key,
            request="https://api.coingecko.com/api/v3/coins/" + task + "/market_chart?vs_currency=usd&days=" + days,
        )
        data = response.json()
        return data


class FetchTrendingCoinsTool(CoingeckoTool):
    """Tool for retrieving currently trending cryptocurrencies.

    Fetches a list of cryptocurrencies that are currently trending
    on CoinGecko.

    Attributes:
        name (str): Tool identifier for the agent system
        description (str): Description of the tool's functionality
        inputs (dict): Schema for the required input parameters
        output_type (str): Type of data returned by the tool
    """

    name = "fetch_trending_coins"
    description = "This is a tool that returns the trending coins on coingecko."
    inputs = {
        "dummy": {
            "type": "string",
            "description": "Dummy argument to make the tool work",
        }
    }
    output_type = "string"

    def forward(self, dummy: str) -> str:  # pylint: disable=W0221, W0613
        """Fetch currently trending cryptocurrencies.

        Args:
            dummy (str): Unused parameter required by tool interface

        Returns:
            str: JSON string containing trending cryptocurrency data
        """
        response = call_coingecko_api(
            api_key=self.api_key,
            request="https://api.coingecko.com/api/v3/search/trending",
        )
        data = response.json()
        return data


def call_coingecko_api(api_key: str, request: str) -> requests.Response:
    """Make an authenticated request to the Coingecko API.

    Args:
        api_key (str): Coingecko API key for authentication
        request (str): Complete API request URL

    Returns:
        requests.Response: Response from the Coingecko API

    Note:
        Includes a 30-second timeout for API requests
    """
    headers = {"accept": "application/json", "x-cg-demo-api-key": api_key}
    return requests.get(
        request,
        headers=headers,
        timeout=30,
    )


if __name__ == "__main__":
    get_coin_price = GetCoinPriceTool()
    print(get_coin_price.forward("ethereum"))
