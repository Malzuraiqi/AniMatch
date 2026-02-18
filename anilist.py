import requests

API_URL = 'https://graphql.anilist.co'
user_id = None

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

    global user_id
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

def get_trending_list():
    user_lists_query = """
        query Query($type: MediaType, $userId: Int) {
        MediaListCollection(type: $type, userId: $userId) {
            lists {
            entries {
                mediaId
            }
            }
        }
        }
    """

    user_lists_response = requests.post(
        API_URL,
        json={
            'query': user_lists_query,
            'variables': {'type': 'ANIME', 'userId': user_id}
        },
        timeout=15,
    )

    user_lists = user_lists_response.json()
    media_ids = [entry['mediaId'] 
             for media_list in user_lists['data']['MediaListCollection']['lists'] 
             for entry in media_list['entries']]
    
    trending_list_query = """
        query ($page: Int, $perPage: Int, $idNotIn: [Int]) {
        Page(page: $page, perPage: $perPage) {
            media(type: ANIME, sort: TRENDING_DESC, id_not_in: $idNotIn) {
            id
            title {
                english
                romaji
            }
            genres
            averageScore
            popularity
            siteUrl
            coverImage {
                large
                extraLarge
            }
            tags {
                name
                rank
            }
            studios {
                nodes {
                    name
                }
            }
            }
        }
        }
        """
    
    trending_list_response = requests.post(
        API_URL,
        json={
            'query': trending_list_query,
            'variables': {'page': 1, 'perPage': 50, 'idNotIn': media_ids}
        },
        timeout=15,
    )

    trending_list = trending_list_response.json()

    trending = []
    for media in trending_list['data']['Page']['media']:
        trending.append(media)

    return trending    

def normalize_anime(media, get_url=False):
    title_data = media.get('title') or {}
    
    # Get top 3 tags by rank
    tags = media.get('tags') or []
    top_tags = sorted(tags, key=lambda x: x.get('rank', 0), reverse=True)[:3]
    tag_names = [tag.get('name') for tag in top_tags]
    
    # Get top 3 studios
    studios_data = media.get('studios') or {}
    studios_nodes = studios_data.get('nodes') or []
    studio_names = [studio.get('name') for studio in studios_nodes][:3]
    
    # Get description first 150 chars
    description = media.get('description') or ''
    short_description = description[:150] + '...' if len(description) > 150 else description
    
    base_data = {
        'id': media.get('id'),
        'title': title_data.get('english') or title_data.get('romaji') or 'Unknown Title',
        'cover_image': (media.get('coverImage') or {}).get('large'),
        'genres': (media.get('genres') or [])[:3],
        'mean_score': media.get('averageScore'),
        'tags': tag_names,
        'studios': studio_names,
        'description': short_description
    }
    
    if get_url:
        base_data['site_url'] = media.get('siteUrl')
    
    return base_data