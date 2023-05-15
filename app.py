import os
import logging
import requests
from flask import Flask, jsonify, render_template


app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIException(Exception):
    """Custom exception class for API-related errors."""
    pass


class DataService:
    """Class responsible for fetching data from the API and caching the results."""
    def __init__(self, api_key: str):
        """
        Initialize the DataService with the provided API key.

        Args:
            api_key (str): API key for accessing the weather data.
        """
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.cache = {}

    def fetch_data(self, endpoint: str, params: dict) -> dict:
        """
        Fetch data from the API for a specific endpoint and set of parameters.

        Args:
            endpoint (str): The API endpoint to fetch data from.
            params (dict): Dictionary of parameters to include in the API request.

            Returns:
                dict: The JSON response data from the API.

            Raises:
                APIException: If there is an error during data retrieval.
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            params["appid"] = self.api_key
            cache_key = self.generate_cache_key(endpoint, params)

            if cache_key in self.cache:
                return self.cache[cache_key]

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            self.cache[cache_key] = data
            return data
        except requests.exceptions.RequestException as e:
            logger.error("Error occurred during data retrieval: %s", str(e))
            raise APIException("Failed to fetch data from the API.")

    def generate_cache_key(self, endpoint: str, params: dict) -> str:
        return f"{endpoint}-{hash(frozenset(params.items()))}"


@app.route('/')
def index():
    return render_template('weather.html')


@app.route('/weather/<city>')
def get_weather(city):
    if not city or not city.isalpha():
        logger.warning("Invalid city name: %s", city)
        return jsonify({"error": "Invalid city name."}), 400

    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not api_key:
        logger.error("API key is not provided.")
        return jsonify({"error": "API key is not configured properly."}), 500

    data_service = DataService(api_key)

    try:
        params = {"q": city, "units": "metric"}
        data = data_service.fetch_data("weather", params)
        temperature = data['main']['temp']
        weather = data['weather'][0]['description']
        response = {"city": city, "temperature": temperature, "weather": weather}
        logger.info("Weather data retrieved for city: %s", city)
        return jsonify(response)
    except APIException as e:
        logger.error("Data processing failed: %s", str(e))
        return jsonify({"error": "Failed to retrieve weather data."}), 500
    except requests.exceptions.RequestException as e:
        logger.error("Error occurred during data retrieval: %s", str(e))
        return jsonify({"error": "Failed to retrieve data from the API."}), 500


if __name__ == '__main__':
    # Load environment variables from a .env file if it exists
    from dotenv import load_dotenv
    load_dotenv()
    # Start the application
    app.run(debug=True)
