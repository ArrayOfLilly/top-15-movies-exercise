from pprint import pprint
import requests
import sqlalchemy
from flask import Flask, render_template, request, redirect, flash, url_for
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import UniqueConstraint
from wtforms import StringField, TextAreaField, IntegerField, FloatField, RadioField, SubmitField
from wtforms.validators import DataRequired
from time import sleep


moviedb_search_movie_url = "https://api.themoviedb.org/3/search/movie"
moviedb_search_movie_details_url = f"https://api.themoviedb.org/3/movie/"
moviedb_poster_url = "https://image.tmdb.org/t/p/w600_and_h900_bestv2/"
moviedb_api_key = "7452d75a822f1cfb50e0a60b127575d4"
moviedb_read_token = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI3NDUyZDc1YTgyMmYxY2ZiNTBlMGE2MGIxMjc1NzVkNCIsInN1YiI6IjY1NDZmYmIxMjg2NmZhMDBmZWZmNjUzMSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.aA5tAqNBhu3t3OyL5shqC_P_vLvedL0cNEUWW-krWik"
headers = {
	"accept": "application/json",
	"Authorization": f"Bearer {moviedb_read_token}"
}


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'

bootstrap = Bootstrap5(app)
app.config['BOOTSTRAP_BTN_STYLE'] = "dark"

db = SQLAlchemy()
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies-collection.db"
db.init_app(app)


class Movie(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String, unique=False, nullable=False)
	year = db.Column(db.Integer, unique=False, nullable=False)
	director = db.Column(db.String, unique=False, nullable=False)
	synopsis = db.Column(db.String, unique=False, nullable=False)
	rating = db.Column(db.Float, unique=False, nullable=True)
	ranking = db.Column(db.Integer, unique=True, nullable=True)
	review = db.Column(db.String, unique=False, nullable=True)
	img_url = db.Column(db.String, unique=False, nullable=False)
	img_local = db.Column(db.Boolean, unique=False, nullable=False)
	__table_args__ = (UniqueConstraint('title', 'year', 'director', name='tyd'),)


class MovieForm(FlaskForm):
	title = StringField('Title', validators=[DataRequired(message='Please enter the movie title here.')])
	year = IntegerField('Release Year', validators=[DataRequired(message='Please enter the release year here.')])
	director = StringField('Director', validators=[DataRequired(message='Please enter the director\'s name here.')])
	synopsis = TextAreaField('Synopsis', validators=[DataRequired(message='Please enter the synopsis here.')])
	rating = FloatField('Rating', validators=[DataRequired(message="Please rate the book 0.0-10.0")])
	ranking = IntegerField('Personal Ranking', validators=[DataRequired(message="Please rank the movie.")])
	review = TextAreaField('Personal Review', validators=[DataRequired(message='Please enter your review here.')])
	img_url = StringField('Image URL', validators=[DataRequired(message='Please add an image URL here.')])
	img_local = RadioField('Where is your image stored?', choices=['Remote Image URL', 'Local image'],
						   validators=[DataRequired(message='Please choose your image type.')])
	submit = SubmitField('Submit')


# TODO Custom Image URL validator function depending on img_local
def validate_img_url():
	pass


class EditMovieForm(FlaskForm):
	rating = FloatField('Rating')
	ranking = IntegerField('Personal Ranking')
	review = TextAreaField('Personal Review')
	img_url = StringField('Image URL')
	submit = SubmitField('Submit')


class MovieFromForm(FlaskForm):
	title = StringField('Title', validators=[DataRequired(message='Please enter the movie title here.')])
	submit = SubmitField('Submit')


with app.app_context():
	db.create_all()


@app.route("/")
def home():
	with app.app_context():
		result = db.session.execute(db.select(Movie).order_by(Movie.ranking))
		movies = result.scalars()
		all_movies = []
		for movie in movies:
			all_movies.append(movie)
	return render_template('index.html', movies=all_movies)


@app.route("/add", methods=['GET', 'POST'])
def add():
	form = MovieForm()
	if request.method == 'GET':
		return render_template('add.html', form=form)
	elif request.method == 'POST' and form.validate_on_submit():
		if form.img_local == 'Local Image':
			is_local = True
		else:
			is_local = False
		movie = {
			"title": form.title.data,
			"year": form.year.data,
			"director": form.director.data,
			"synopsis": form.synopsis.data,
			"rating": form.rating.data,
			"ranking": form.ranking.data,
			"review": form.review.data,
			"img_url": form.img_url.data,
			"img_local": is_local
		}
		stored_movie = Movie(
			title=movie['title'],
			year=movie['year'],
			director=movie['director'],
			synopsis=movie['synopsis'],
			rating=movie['rating'],
			ranking=movie['ranking'],
			review=movie['review'],
			img_url=movie['img_url'],
			img_local=movie['img_local']

		)
		try:
			with app.app_context():
				db.session.add(stored_movie)
				db.session.commit()
		except sqlalchemy.exc.IntegrityError:
			flash('This Movie is already exists.')
			return render_template('add.html', form=form)
		return redirect('.')
	else:
		return render_template('add.html', form=form)


@app.route("/addfrom", methods=['GET', 'POST'])
def add_from():
	form = MovieFromForm()
	if request.method == 'GET':
		return render_template('addfrom.html', form=form)
	elif request.method == 'POST' and form.validate_on_submit():
		parameters = {
			'query': form.title.data,
			'include_adult': True,
			'page': 1,
		}
		response = requests.get(url=moviedb_search_movie_url, params=parameters, headers=headers)
		data = response.json()['results']
		movie_list = []
		for item in data:
			movie = {
				'id': item['id'],
				'title': item['title'],
				'release_date': item['release_date'],
				'url': f"https://www.themoviedb.org/movie/{item['id']}"
			}
			movie_list.append(movie)
		return render_template('select.html', movies=movie_list)
	else:
		return render_template('addfrom.html', form=form)


@app.route("/details", methods=['GET', 'POST'])
def get_movie_details():
	movie_id = str(request.args.get("id"))
	url = moviedb_search_movie_details_url + movie_id
	res = requests.get(url=url, headers=headers)
	data = res.json()
	movie = Movie(
		title=data['title'],
		year=data['release_date'][0:3],
		director="",
		synopsis=data['overview'],
		rating=data['vote_average'],
		ranking="",
		review="",
		img_url= moviedb_poster_url + data['poster_path'],
		img_local=True
	)
	url = url + '/credits'
	res = requests.get(url=url, headers=headers)
	crew = res.json()['crew']
	for role in crew:
		if role['known_for_department'] == 'Directing':
			movie.director = role['name']
			try:
				with app.app_context():
					db.session.add(movie)
					db.session.commit()
					return redirect(url_for("edit", id=movie.id))
			except sqlalchemy.exc.IntegrityError:
				flash('This Movie is already exists.')
				render_template('../')
	return redirect('../')


@app.route("/edit", methods=['GET', 'POST'])
def edit():
	print('edit')
	form = EditMovieForm()
	movie_id = request.args.get('id')
	print(movie_id)
	if request.method == 'GET':
		with app.app_context():
			movie = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
		return render_template('edit.html', form=form, movie=movie)
	elif request.method == 'POST':
		with app.app_context():
			movie_to_update = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
			if form.rating.data:
				movie_to_update.rating = form.rating.data
			if form.ranking.data:
				movie_to_update.ranking = form.ranking.data
			if form.review.data:
				movie_to_update.review = form.review.data
			if form.img_url.data:
				movie_to_update.img_url = form.img_url.data
				movie_to_update.img_local = False
			try:
				db.session.commit()
			except sqlalchemy.exc.IntegrityError:
				flash('This Ranking is already taken.')
		return redirect('../')
	else:
		return redirect('../')


@app.route("/del", methods=['GET', 'POST'])
def delete():
	movie_id = request.args.get('id')
	with app.app_context():
		movie = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
		db.session.delete(movie)
		db.session.commit()
	return redirect('../')


if __name__ == '__main__':
	app.run(debug=True)
