from flask import Flask, render_template, request, session, flash, redirect, url_for
from anilist import fetch_user_lists, normalize_anime
from dotenv import load_dotenv
import os, uuid, random
import requests
from gemini import get_recommendations

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
MAX_ANIME_TO_RATE = 10
RATING_STATE = {}

# this is called a decorator, you could add variables to it using <variable_name>
# to use that variable just add it as an argument to the function like index(variable_name)
# to add a converter (specify the type) just add the converter <converter:variable_name>
# converters: none(string), int, path, float, uuid
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        flashes = session.get('_flashes')
        session.clear()
        if flashes:
            session['_flashes'] = flashes
        return render_template('index.html')

    if request.method == 'POST':
        session.clear()
        username = request.form.get('username', '').strip()

        if not username:
            flash('Please enter an AniList username.', 'neutral')
            return redirect(url_for('index'))

        try:
            completed_list, planning_list = fetch_user_lists(username)
            completed_titles = [anime['title'] for anime in completed_list]
            completed_sample = random.sample(completed_list, MAX_ANIME_TO_RATE)
            normalized_completed = [normalize_anime(anime) for anime in completed_sample]
            normalized_planning = [normalize_anime(anime, get_url=True) for anime in planning_list]
            if not normalized_completed or not normalized_planning:
                flash('No completed or planning anime found for this user.', 'neutral')
                return redirect(url_for('index'))

            state_id = str(uuid.uuid4())
            completed_sample = []
            anime_by_id = {}
            for anime in normalized_completed:
                anime_id = anime.get('id')
                anime_by_id[anime_id] = anime
                completed_sample.append(anime_id)

            planning_ids = []
            for anime in normalized_planning:
                anime_id = anime.get('id')
                anime_by_id[anime_id] = anime
                planning_ids.append(anime_id)
                

            RATING_STATE[state_id] = {
                'username': username,
                'completed_sample': completed_sample,
                'completed_titles': completed_titles,
                'planning_ids': planning_ids,
                'anime_by_id': anime_by_id,
                'ratings': [],
                'current_index': 0,
            }
            session['state_id'] = state_id
            return redirect(url_for('rate'))
        except requests.exceptions.Timeout:
            flash(f'Could not reach AniList in time.', 'error')
        except requests.exceptions.RequestException:
            flash(f'Could not connect to AniList.', 'error')
        except ValueError as exc:
            flash(str(exc), 'error')
        except Exception:
            flash('Could not fetch AniList data right now. Please retry.', 'error')

        return redirect(url_for('index'))

@app.route('/rate', methods=['GET', 'POST'])
def rate():
    state_id = session.get('state_id')
    state = RATING_STATE.get(state_id) if state_id else None
    if not state:
        flash('Start by entering an AniList username.', 'neutral')
        return redirect(url_for('index'))

    completed_sample = state.get('completed_sample', [])
    total = len(completed_sample)
    current_index = state.get('current_index', 0)

    if request.method == 'POST':
        rating = int(request.form.get('rating'))
        feedback = request.form.get('feedback', '').strip()

        current_anime_id = completed_sample[current_index]
        current_anime = (state.get('anime_by_id') or {}).get(current_anime_id)
        if not current_anime:
            flash('Anime data is no longer available. Please restart rating.', 'neutral')
            return redirect(url_for('index'))

        ratings = state.get('ratings', [])
        ratings.append({
            'anime_id': current_anime.get('id'),
            'title': current_anime.get('title'),
            'rating': rating,
            'feedback': feedback,
        })
        state['ratings'] = ratings

        current_index += 1
        state['current_index'] = current_index

        if current_index >= total:
            flash('Ratings saved', 'success')
            return redirect(url_for('recommendation'))

        return redirect(url_for('rate'))

    anime_id = completed_sample[current_index]
    anime = (state.get('anime_by_id') or {}).get(anime_id)
    if not anime:
        flash('Anime data is no longer available. Please restart rating.', 'neutral')
        return redirect(url_for('index'))

    return render_template(
        'rate.html',
        anime=anime,
        current_index=current_index + 1,
        total=total,
    )

@app.route('/recommendation')
def recommendation():
    state_id = session.get('state_id')
    state = RATING_STATE.get(state_id) if state_id else None
    if not state:
        flash('Start by entering an AniList username.', 'neutral')
        return redirect(url_for('index'))
    ratings = state.get('ratings')
    planning_ids = state.get('planning_ids')
    if not ratings or not planning_ids:
        flash("Couldn't find information for this user", 'neutral')
        return redirect(url_for('index'))
    
    completed_titles = state.get('completed_titles')
    planning_list = [state.get('anime_by_id').get(anime_id) for anime_id in planning_ids]
    try:
        continuations, new_recommendations, trending_recommendations = get_recommendations(ratings, planning_list, completed_titles)
    except Exception as exc:
        app.logger.exception('Failed to generate recommendations')
        flash('Could not generate recommendations right now. Please retry in a moment.', 'error')
        return render_template(
            'recommendation.html',
            continuations=[],
            new_recommendations=[],
            trending_recommendations=[]
        ), 503
    
    return render_template(
        'recommendation.html',
        continuations=continuations,
        new_recommendations=new_recommendations,
        trending_recommendations=trending_recommendations
    )

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    flash('Server error occurred. Please retry in a moment.', 'neutral')
    return render_template('index.html'), 500

if __name__ == "__main__":
    app.run(debug=True)
