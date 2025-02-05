import requests
from config import USDA_API_KEY


def get_product_calories(product_name):
    url = 'https://api.nal.usda.gov/fdc/v1/foods/search'
    params = {
        'api_key': USDA_API_KEY,
        'query': product_name,
        'pageSize': 1
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        foods = data.get('foods')
        if not foods:
            return None
        first_food = foods[0]
        nutrients = first_food.get('foodNutrients', [])
        for n in nutrients:
            if n.get('nutrientId') == 1008:
                return float(n.get('value'))
    except:
        return None
