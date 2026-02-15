from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import json

load_dotenv()
API_KEY = os.environ.get('GEMINI_API_KEY')

def get_recommendations(ratings, planning_list, completed_titles):
    client = genai.Client(api_key=API_KEY)

    required_fields = ['id','title','genres']
    planning_list_shorten = [{key: anime[key] for key in required_fields} for anime in planning_list]

    contents = f"""
        As an expert Anime Recommendation Engine, your task is to analyze a user's taste and filter their planning list into a structured JSON response.

        ### INPUT DATA
        - User's Rated List: {ratings}
        - User's Planning List: {planning_list_shorten}
        - User's Completed Titles: {completed_titles}

        ### TASK STEPS
        1. **Taste Analysis:** Identify patterns in studios, genres, and specific feedback from the Rated List.
        2. **Category 1 (Continuations):** 
            - Look at **both** the User's Rated List and the User's Completed Titles list.
            - Identify any anime in the Planning List that are direct continuations (sequels, movies, prequels, or same-series spin‑offs) of any title in **either** list.
            - For continuations where the original show was **rated** (i.e., it appears in the Rated List), use its score and feedback to inform the match_score and reason.
            - For continuations where the original show was **completed but not rated** (i.e., it's only in the Completed Titles list), assume the user enjoyed it enough to finish it, and use that as a positive signal.
        3. **Category 2 (New Recommendations):** Select NEW discoveries from the Planning List that match the user's taste. 
        4. **THE 6-TITLE LIMIT & DISTRIBUTION:** - You must return a TOTAL of exactly 6 anime.
            - **Continuations Limit:** Include a maximum of 3 continuations. If there are more than 3, select the 3 with the highest predicted match_score.
            - **Filling the List:** The remaining slots (at least 3, but up to 6 if no continuations exist) MUST be filled with New Recommendations to reach the total of 6.
            - If zero continuations exist, the "continuations" list MUST be an empty array `[]`.

        ### OUTPUT RULES
        - **Strict JSON:** Return ONLY a JSON object. No preamble or conversational filler.
        - **Double Brackets:** Use `{{` and `}}` for the JSON structure to ensure f-string compatibility.
        - **Exact Titles:** The "title" field must match the string in the planning list EXACTLY.
        - **Personalized Reasoning:** The "reason" must use "You" and "Your." It MUST reference specific titles from the user's rated list, their numerical scores, and any quoted feedback they provided.

        ### REQUIRED OUTPUT FORMAT
        {{
        "continuations": [
            {{
            "title": "Exact Title from Planning List",
            "match_score": 9.8,
            "reason": "Since you rated [Show A] a 9/10 and loved the '[Quote]', this sequel is a must-watch..."
            }}
        ],
        "new_recommendations": [
            {{
            "title": "Exact Title from Planning List",
            "match_score": 8.5,
            "reason": "Because you enjoyed the dark atmosphere of [Show B] (8/10), this [Studio] production offers a similar vibe..."
            }}
        ]
        }}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=contents,
        config=types.GenerateContentConfig(response_mime_type='application/json')
    )

    return merge_recommendations(response.text, planning_list)

def merge_recommendations(response, planning_list):
    recomendations = json.loads(response)

    lookup = {item['title']: item for item in planning_list}

    def merge(rec_list):
        merged_list = []
        for rec in rec_list:
            title = rec['title']
            if title in lookup:
                full_list = lookup[title].copy()
                full_list.update(rec)
                merged_list.append(full_list)
        return merged_list

    continuations = merge(recomendations.get('continuations', []))
    new_recommendations = merge(recomendations.get('new_recommendations', []))

    return continuations, new_recommendations