from dotenv import load_dotenv
from anilist import get_trending_list, normalize_anime
import os
import json
import requests

load_dotenv()
API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent'
api_url = f"{GEMINI_API_URL}?key={API_KEY}"

def get_recommendations(ratings, planning_list, completed_titles):
    required_fields = ['id','title','genres']
    planning_list_shorten = [{key: anime[key] for key in required_fields} for anime in planning_list]

    trending_list = get_trending_list()
    normalized_trending = [normalize_anime(anime, get_url=True) for anime in trending_list]
    trending_list_shorten = [{key: anime[key] for key in required_fields} for anime in normalized_trending]

    contents = f"""
        As an expert Anime Recommendation Engine, your task is to analyze a user's taste and filter their planning list into a structured JSON response.

        ### INPUT DATA
        - User's Rated List: {ratings}
        - User's Planning List: {planning_list_shorten}
        - User's Completed Titles: {completed_titles}
        - Trending Anime List: {trending_list_shorten}

        Recommend top must-watch animes based on the user's rated list, planning list, completed titles, and trending anime list. 

        Consider the following for recommendations:
        - Analyze the genres and tags from the user's highly-rated anime.
        - Review the reasons provided for their ratings.
        - Take into account studio preferences.
        - Examine themes and story elements from anime descriptions.
        - Identify patterns in their rating behavior.

        ### Output Rules
        - **Strict JSON:** Return ONLY a JSON object. No preamble or conversational filler.
        - **Exact Titles:** The "title" field must match the string in the planning list EXACTLY.
        - **Personalized Reasoning:** Provide detailed reasoning explaining why each recommendation matches the user's preferences.
        - **Matching Elements:** Include key matching elements that justify the recommendations.
        - **Trending Recommendations:** for the trending recommendations make sure they are taken from the Trending Anime List only
        - **Limits:** 
            - A maximum of 4 new recommendations.
            - A maximum of 3 continuations.
            - A maximum of 3 trending recommendations.

        ### Required Output Format
        {{
        "continuations": [
            {{
            "title": "Exact Title from Planning List",
            "match_score": 9.8,
            "reason": "Since you rated [Show A] a 9/10 and loved the '[Quote]', this sequel is a must-watch...",
            "matchingElements": ["element1", "element2", "element3"]
            }}
        ],
        "new_recommendations": [
            {{
            "title": "Exact Title from Planning List",
            "match_score": 8.5,
            "reason": "Based on your love of X and Y, this anime features...",
            "matchingElements": ["element1", "element2", "element3"]
            }}
        ],
        "trending_recommendations": [
            {{
            "title": "Exact Title from Planning List",
            "match_score": 8.5,
            "reason": "Based on your love of X and Y, this anime features...",
            "matchingElements": ["element1", "element2", "element3"]
            }}
        ]
        }}
    """

    response = requests.post(
        api_url,
        headers={'Content-Type': 'application/json'},
        json={
            'contents': [{
                'parts': [{'text': contents}]
            }],
            'generationConfig': {
                'temperature': 0.7,
                'response_mime_type': 'application/json'
            }
        },
        timeout=30
    )

    response_data = response.json()
    response_text = response_data['candidates'][0]['content']['parts'][0]['text']

    return merge_recommendations(response_text, planning_list, normalized_trending)

def merge_recommendations(response, planning_list, trending_list):
    recomendations = json.loads(response)

    lookup = {item['title']: item for item in planning_list}
    for item in trending_list:
        lookup[item['title']] = item

    def merge(rec_list):
        merged_list = []
        for rec in rec_list:
            title = rec.get('title')
            if title in lookup:
                full_list = lookup[title].copy()
                full_list.update(rec)
                merged_list.append(full_list)
        return merged_list

    continuations = merge(recomendations.get('continuations', []))
    new_recommendations = merge(recomendations.get('new_recommendations', []))
    trending_recommendations = merge(recomendations.get('trending_recommendations', []))

    return continuations, new_recommendations, trending_recommendations