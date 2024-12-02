import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os

class PokemonCardAPI:
    """
    Class to manage Pokemon card data from TCG API.
    Handles data fetching, cleaning, and price updates.
    """
    
    def __init__(self, api_url="https://api.pokemontcg.io/v2/cards"):
        self.api_url=api_url
        self.variables_to_drop=[
                    'attacks',
                   'supertype',
                   'hp',
                   'abilities',
                   'types',
                   'level',
                   'evolvesFrom',
                   'evolvesTo',
                   'weaknesses',
                   'resistances',
                   'retreatCost',
                   'convertedRetreatCost',
                   'flavorText',
                   'legalities',
                    'images',
                    'rules',
                    'regulationMark',
                    'ancientTrait',
                    'number',
                    'set',
                    'subtypes',
                    'tcgplayer',
                    'cardmarket',
                    'url']
        self.columns_order=[
            "id",
            "name",
            "rarity",
            "collection",
            "series",
            "holofoil_price",
            "reverse_holofoil_price",
            "release_date",
            "nationalPokedexNumbers",
            "artist"]
    
    
    def import_data(self):
        """
        Retrieves all available cards from the Pokemon TCG API.
        
        Returns:
            pandas.DataFrame: DataFrame containing all cards with their raw information
            
        Example:
            df = import_data()
            # Returns a DataFrame with columns like id, name, rarity, etc.
        """
        page = 1
        all_cards = []
        
        while True:
            params = {"page": page, "pageSize": 250}
            response = requests.get(self.api_url, params=params)

            if response.status_code == 200:
                data = response.json()["data"]
                if not data:
                    break
                all_cards.extend(data)
                page += 1
            else:
                print(f"Erreur: {response.status_code}")
                break
                
        return pd.DataFrame(all_cards)
    
    
    def _get_prices(self, card, threshold=5):
        """
        Extracts holofoil and reverse holofoil prices for a card.
        
        Args:
            x (dict): Dictionary containing card information
            
        Returns:
            tuple: (url, holofoil_price, reverse_holofoil_price)
            
        Note:
            Returns None values if the card is common or prices are below threshold
        """        
        if pd.isna(card["tcgplayer"]) or card["rarity"] == "Common" or pd.isna(card["rarity"]):
            return None, None, None
        
        prices = card["tcgplayer"].get("prices", {})
        holofoil_data = prices.get("holofoil", {})
        reverse_holofoil_data = prices.get("reverseHolofoil", {})

        holofoil_price = holofoil_data.get("market", None)
        reverse_holofoil_price = reverse_holofoil_data.get("market", None)

        if (holofoil_price is not None and holofoil_price > threshold) or (reverse_holofoil_price is not None and reverse_holofoil_price > threshold):
            return card["tcgplayer"].get("url", None), holofoil_price, reverse_holofoil_price
        return None, None, None
    
    
    def filter_cards(self, df, threshold=5):
        """
        Cleans and filters card data based on rarity and price.
        
        Args:
            df (pandas.DataFrame): DataFrame containing raw data
            threshold_price (float, optional): Minimum price to keep a card. Defaults to 5.
            
        Returns:
            pandas.DataFrame: Cleaned DataFrame containing only valuable cards
            
        Note:
            - Removes common cards
            - Keeps only cards above threshold price
            - Extracts collection and series information
            - Removes unnecessary columns
        """        
        df[["url", "holofoil_price", "reverse_holofoil_price"]] = df.apply(self._get_prices, axis=1, result_type="expand")
        df_cleaned = df.dropna(subset=["url"])
        df_cleaned = df_cleaned[
            (df_cleaned["rarity"] != "Common") & 
            ((df_cleaned["holofoil_price"] > threshold) | 
             (df_cleaned["reverse_holofoil_price"] > threshold))
        ]
        
        df_cleaned["collection"] = df_cleaned["set"].apply(lambda x: x["name"])
        df_cleaned["series"] = df_cleaned["set"].apply(lambda x: x["series"])
        df_cleaned["release_date"] = df_cleaned["set"].apply(lambda x: x.get("releaseDate", None))
        
        df_cleaned = df_cleaned.drop(columns=self.variables_to_drop, errors='ignore')
        return df_cleaned[self.columns_order]

    def process_cards(self):
        """Main method to process all cards"""
        df = self.import_data()
        return self.filter_cards(df)
    

class PokemonCardDatabase:
    """Class to handle Pokemon card database operations"""
    def __init__(self, api_handler: PokemonCardAPI):
        self.api_handler = api_handler
    
    def update_database(self, csv_path='pokemon_cards.csv'):
        """
    Creates or updates the Pokemon cards CSV file with current market prices.
    
    This function performs several operations:
    1. Imports new data from the Pokemon TCG API
    2. Cleans and filters the data based on rarity and price thresholds
    3. Updates prices for existing cards
    4. Adds new cards to the database
    5. Saves both a main file and a timestamped backup
    
    Args:
        csv_path (str, optional): Path to the main CSV file. 
            Defaults to 'pokemon_cards.csv'.
    
    Returns:
        pandas.DataFrame: Updated DataFrame containing all Pokemon cards data.
        None: If an error occurs during the process.
    
    File Structure:
        The CSV contains the following columns:
        - id: Unique card identifier (e.g., 'dp3-3', 'base6-3')
        - name: Pokemon name
        - rarity: Card rarity (Rare Holo, Rare, Uncommon)
        - collection: Set name (e.g., Secret Wonders, Emerald)
        - series: Card series (Diamond & Pearl, EX, Base)
        - holofoil_price: Market price for holofoil version
        - reverse_holofoil_price: Market price for reverse holofoil version
        - release_date: Card release date (YYYY/MM/DD)
        
    Example:
        >>> df = update_pokemon_cardsultimate()
        Base de données mise à jour : 3955 cartes
        Fichier principal : pokemon_cards.csv
        Copie de sauvegarde : pokemon_cards_20240302_1430.csv
    """
        
        # Import new data using the API handler
        new_df = self.api_handler.import_data()
        new_df_cleaned = self.api_handler.filter_cards(new_df)
        
        try:
            if os.path.isfile(csv_path):
                old_df = pd.read_csv(csv_path)
                # Update existing cards prices
                for idx, row in old_df.iterrows():
                    card_id = row['id']
                    if card_id in new_df_cleaned['id'].values:
                        new_prices = new_df_cleaned[new_df_cleaned['id'] == card_id].iloc[0]
                        old_df.at[idx, 'holofoil_price'] = new_prices['holofoil_price']
                        old_df.at[idx, 'reverse_holofoil_price'] = new_prices['reverse_holofoil_price']
                
                # Add new cards
                new_cards = new_df_cleaned[~new_df_cleaned['id'].isin(old_df['id'])]
                updated_df = pd.concat([old_df, new_cards], ignore_index=True)
            else:
                updated_df = new_df_cleaned
            
            # Save files
            self._save_database(updated_df, csv_path)
            return updated_df
            
        except Exception as e:
            print(f"Error updating database: {e}")
            return None

    def _save_database(self, df, csv_path):
        """Saves the database with a timestamped backup"""
        # Supprime l'ancien fichier s'il existe
        if os.path.exists(csv_path):
            os.remove(csv_path)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        backup_path = f'pokemon_cards_{timestamp}.csv'
        
        # Sauvegarde les nouveaux fichiers
        df.to_csv(backup_path, index=False, encoding='utf-8', float_format='%.2f')
