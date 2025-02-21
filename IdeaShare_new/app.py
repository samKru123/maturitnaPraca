import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from werkzeug.utils import secure_filename



app = Flask(__name__)
app.secret_key = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ideashare.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

CATEGORIES = ["Programovanie", "Elektrotechnika", "Siete", "Iné"]

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

working_on = db.Table('working_on',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('idea_id', db.Integer, db.ForeignKey('idea.id'), primary_key=True)
)


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Funkcia na kontrolu správneho formátu súboru
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Idea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    #category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='idea', lazy=True)  # Prepojenie na komentáre
    upvotes = db.Column(db.Integer, default=0)
    categories = db.Column(db.String(255), nullable=True)
    image = db.Column(db.String(255), nullable=True)  # Tu bude cesta k obrázku
    working_users = db.relationship('User', secondary=working_on, backref=db.backref('working_ideas', lazy='dynamic'))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    idea_id = db.Column(db.Integer, db.ForeignKey('idea.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref='comments')  # Relácia na používateľa

class Upvote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    idea_id = db.Column(db.Integer, db.ForeignKey('idea.id'), nullable=False)
    # Unikátna kombinácia užívateľ & nápad – zabráni duplikátnemu hlasovaniu
    __table_args__ = (db.UniqueConstraint('user_id', 'idea_id', name='unique_user_idea'),)

# Routes
@app.route('/')
def home():
    categories = ['Elektrotechnika', 'Programovanie', 'Siete', 'Iné']
    selected_category = request.args.get('category')
    search_query = request.args.get('search', '')

    if selected_category:
        ideas = Idea.query.filter(Idea.categories.contains(selected_category)).all()
    else:
        ideas = Idea.query.all()

    if search_query:
        ideas = ideas.filter(Idea.title.contains(search_query) | Idea.description.contains(search_query))

    #ideas = ideas.all()
    return render_template('index.html', ideas=ideas, categories=CATEGORIES, selected_category=selected_category)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('home'))
        flash('Invalid credentials!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/add_idea', methods=['GET', 'POST'])
def add_idea():
    if 'user_id' not in session:
        flash('You must be logged in to add an idea.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        selected_categories = request.form.getlist('categories')  # Získa vybrané kategórie
        user_id = session['user_id']
        image_path = None

        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_path = f'IdeaShare_1/static/uploads/{filename}'

                
                print(image_path)

        # Uloží kategórie ako reťazec oddelený čiarkami
        new_idea = Idea(title=title, description=description,user_id=user_id, categories=",".join(selected_categories), image=image_path)

        db.session.add(new_idea)
        db.session.commit()
        return redirect(url_for('home'))

    print("ooookay")
    return render_template('add_idea.html', categories=CATEGORIES)

@app.route('/admin')
def admin():
    ideas = Idea.query.all()
    return render_template('admin.html', ideas=ideas)

@app.route('/delete_idea/<int:idea_id>')
def delete_idea(idea_id):
    idea = Idea.query.get(idea_id)
    db.session.delete(idea)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/idea/<int:idea_id>')
def idea_detail(idea_id):
    idea = Idea.query.get_or_404(idea_id)
    comments = Comment.query.filter_by(idea_id=idea_id).all()
    return render_template('idea_detail.html', idea=idea, comments=comments)


@app.route('/idea/<int:idea_id>/comment', methods=['POST'])
def add_comment(idea_id):
    if not session.get('user_id'):
        flash("Musíte byť prihlásený na pridanie komentára.", "danger")
        return redirect(url_for('login'))

    content = request.form['content']
    if not content.strip():
        flash("Komentár nemôže byť prázdny!", "danger")
        return redirect(url_for('idea_detail', idea_id=idea_id))

    comment = Comment(content=content, idea_id=idea_id, user_id=session['user_id'])
    db.session.add(comment)
    db.session.commit()
    flash("Komentár bol úspešne pridaný!", "success")
    return redirect(url_for('idea_detail', idea_id=idea_id))



@app.route('/upvote/<int:idea_id>', methods=['POST'])
def upvote_idea(idea_id):
    if 'user_id' not in session:
        flash('You must be logged in to upvote.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    idea = Idea.query.get(idea_id)

    if idea:
        # kontrola ci uz uzivatel hlasoval
        existing_vote = Upvote.query.filter_by(user_id=user_id, idea_id=idea_id).first()
        if existing_vote:
            flash('You have already upvoted this idea.', 'warning')
        else:
            # pridanie hlasu
            upvote = Upvote(user_id=user_id, idea_id=idea_id)
            idea.upvotes += 1
            db.session.add(upvote)
            db.session.commit()
            flash('Upvote added!', 'success')

    return redirect(url_for('home'))


@app.route('/idea/<int:idea_id>/work_on', methods=['POST'])
def work_on_idea(idea_id):
    if 'user_id' not in session:
        flash('Musíš sa prihlásiť, aby si mohol pracovať na nápade.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    idea = Idea.query.get_or_404(idea_id)

    if user in idea.working_users:
        idea.working_users.remove(user)
        flash('Nápad už nemáš označený ako rozpracovaný.', 'warning')
    else:
        idea.working_users.append(user)
        flash('Úspešne si označil nápad ako rozpracovaný.', 'success')

    db.session.commit()
    return redirect(url_for('idea_detail', idea_id=idea_id))


@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    ideas_created = Idea.query.filter_by(user_id=user.id).all()
    ideas_working_on = user.working_ideas  # Many-to-Many vzťah

    return render_template('user_profile.html', user=user, ideas_created=ideas_created, ideas_working_on=ideas_working_on)





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    