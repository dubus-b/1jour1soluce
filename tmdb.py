import requests
import re
import random
import redis
import json

# TMDb API Key and Base URL
API_KEY = ""
BASE_URL = "https://api.themoviedb.org/3"

class TargetMovie:
    def __init__(self, title=None, year=None, tmdb_id=None):
        self.title = title
        self.genres = []
        self.nb_genre = 0
        self.min_date = None # Renommé min_year en min_date
        self.max_date = None  # Renommé max_year en max_date
        self.year = None  # Default year
        self.countries = []
        self.duration = 0
        self.found = False
        self.id = tmdb_id
        self.actors = []
        self.director = None
        
    def dump_info(self):
        info = {
            'Title': self.title,
            'Genres': self.genres,
            'Number of Genres': self.nb_genre,
            'Min Date': self.min_date,
            'Max Date': self.max_date,
            'Year': self.year,
            'Countries': self.countries,
            'Duration (minutes)': self.duration,
            'Found': self.found,
            'TMDB ID': self.id,
            'Actors': self.actors,
            'Director': self.director
        }
        return info

class TMDB_ENGINE:
    
    GENRES_DICT = {
    "Action": 28,
    "Aventure": 12,
    "Animation": 16,
    "Comédie": 35,
    "Crime": 80,
    "Documentaire": 99,
    "Drame": 18,
    "Famille": 10751,
    "Fantastique": 14,
    "Horreur": 27,
    "Musique": 10402,
    "Mystère": 9648,
    "Romance": 10749,
    "Science-fiction": 878,
    "Téléfilm": 10770,
    "Thriller": 53,
    "Guerre": 10752,
    "Western": 37
}
    
    test_year = None
    def __init__(self):
        
        self.api_key = API_KEY
        self.url = BASE_URL
        self.movie = TargetMovie()
        
    def extraire_annee(self, str):
        motif = r'\b\d{4}\b'
        resultat = re.search(motif, str)
        return int(resultat.group())
        
        
        
    def _clue_year(self, str):
        if "avant" in str:
            self.movie.max_date = self.extraire_annee(str)  
        elif "après" in str:
            self.movie.min_date = self.extraire_annee(str)
        elif "entre" in str:
            y = re.findall(r'\d+', str)
            self.movie.max_date = int(y[1])
            self.movie.min_date = int(y[0])
        else :
            self.movie.max_date = self.extraire_annee(str)
            self.movie.min_date = self.extraire_annee(str)
            self.movie.year = self.extraire_annee(str)                           
        
        
    def parse_clue(self, clues):
        # Initialiser les variables
        genres = []
        year = None
        duree = ''
        for item in clues:
            if item == '' or bool(re.search(r'\d', item)):
                break  
            if item == '- - - -':
                del item
            else:
                genres.append(item)
                del item

        genre_ids = [str(self.GENRES_DICT[genre]) for genre in genres if genre in self.GENRES_DICT]
        self.movie.genre = genre_ids

        annee = [elem for elem in clues if re.search(r'\b(19|20)\d{2}\b', elem)]

        if annee:
            self._clue_year(annee[0])

       

    def get_actor_id(self, actor_name):
        url = f'{self.url}/search/person?api_key={self.api_key}&query={actor_name}'
        
        # Make the GET request
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            # Check if any results were found
            if data['results']:
                # Assuming the first result is the correct one
                actor_id = data['results'][0]['id']
                if data['results'][0]['known_for_department'] == "Directing":
                    self.movie.director = actor_id
                    return None
                return actor_id
            else:
                return None
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return None
        
    def check_data(self, movie):
        date = int(movie['release_date'].split("-")[0])
        return self.movie.min_date <= date <= self.movie.max_date 
        
    def set_actors(self, actors):
        actors = list(filter(None, actors))
        ids = []
        for actor in actors:
            actor_id = self.get_actor_id(actor)
            if actor_id is not None:
                ids.append(actor_id)
        self.movie.actors = ids

    def get_popular_movies(self, num_results=6):
        """
        Fetch popular movies from TMDB API for a specified year.

        Args:
            num_results (int): The maximum number of results to return.

        Returns:
            list: A list of popular movies.
        """
        movies = []
        page = 1
        while len(movies) < num_results:
            params = {
                'api_key': self.api_key,
                'sort_by': 'popularity.desc',
                'primary_release_year': self.movie.year,
                'page': page
            }
            if self.movie.genres:
                params['with_genres'] = ','.join(self.movie.genre)
                
            if self.movie.actors:
                params['with_cast'] = ','.join(map(str, self.movie.actors))
                
            if self.movie.director:
                params['with_crew'] = str(self.movie.director)
                
            if self.movie.year and not self.movie.actors:
                params['primary_release_year'] = self.movie.year,

                

            try:
                response = requests.get(f'{self.url}/discover/movie', params=params)
                response.raise_for_status()  # Raise an error for bad responses
                data = response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error fetching data for year {self.movie.year}, page {page}: {e}")
                break  # Exit the loop on error

            results = data.get('results', [])

            if not results:
                break

            movies.extend(results)

            if len(results) < 20:  # TMDb usually returns 20 results per page
                break
        
            page += 1
        self.add_movies_to_queue(movies[:num_results])



        try:
            # Make the GET request to discover a movie
            response = requests.get(f'{self.url}/discover/movie', params=params)
            response.raise_for_status()  # Raise an error for bad responses

            # Get the results from the response
            data = response.json()
            results = data.get('results', [])
            # Check if any results were found
            if results:
                self.add_movies_to_queue([results[0]])
            else:
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching movie for year {year}: {e}")
            return None

    def add_movies_to_queue(self, movies):
        r = redis.Redis(host='localhost', port=6379, db=0)

        # Ajouter les films à la queue Redis
        for movie in movies:
            # Sérialiser le film en JSON
            json_movie = json.dumps(movie)
            r.lpush('movie_queue', json_movie)
            print(movie)
            print(f"Film ajouté à la queue Redis: {movie['title']}")
