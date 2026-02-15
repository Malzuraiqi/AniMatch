import requests

API_URL = 'https://graphql.anilist.co'

# rank (Int): The relevance ranking of the tag out of the 100 for this media
def fetch_user_lists(username):
    user_id_query = """
        query ($username: String) {
            User(name: $username) {
                id
                name
            }
        }"""

    lists_query = """
        query ($userId: Int, $type: MediaType) {
            completed: MediaListCollection(userId: $userId, type: $type, status: COMPLETED) {
                lists {
                    entries {
                        media {
                            id
                            title {
                                english
                                romaji
                            }
                            siteUrl
                            coverImage {
                                large
                                extraLarge
                            }
                            genres
                            tags {
                                name
                                rank
                            }
                            averageScore
                            studios {
                                nodes {
                                    name
                                }
                            }
                            description
                        }
                    }
                }
            }
            planning: MediaListCollection(userId: $userId, type: $type, status: PLANNING) {
                lists {
                    entries {
                        media {
                            id
                            title {
                                english
                                romaji
                            }
                            siteUrl
                            coverImage {
                                large
                                extraLarge
                            }
                            genres
                            tags {
                                name
                                rank
                            }
                            averageScore
                            studios {
                                nodes {
                                    name
                                }
                            }
                            description
                        }
                    }
                }
            }
        }
    """

    user_response = requests.post(
        API_URL,
        json={
            'query': user_id_query,
            'variables': {'username': username}
        },
        timeout=15,
    )
    user_response.raise_for_status() # checks if the response had an unsuccessful status code
    user_payload = user_response.json()

    if user_payload.get('errors'):
        raise ValueError(user_payload['errors'][0].get('message', 'Could not find AniList user.'))

    user_id = user_payload['data']['User']['id']

    lists_response = requests.post(
        API_URL,
        json={
            'query': lists_query,
            'variables': {
                'userId': user_id,
                'type': 'ANIME'
            }
        },
        timeout=30,
    )
    lists_response.raise_for_status()
    lists_payload = lists_response.json()

    if lists_payload.get('errors'):
        raise ValueError(lists_payload['errors'][0].get('message', 'Could not fetch anime lists.'))

    completed = []
    for list_item in lists_payload['data']['completed']['lists']:
        for entry in list_item['entries']:
            completed.append(entry['media'])

    planning = []
    for list_item in lists_payload['data']['planning']['lists']:
        for entry in list_item['entries']:
            planning.append(entry['media'])

    return completed, planning
