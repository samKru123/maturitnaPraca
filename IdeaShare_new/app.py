import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash



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
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Len jeden môže mať True
    is_category_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)  # Nový stĺpec pre blokovanie
    comments = db.relationship('Comment', backref='user', lazy=True, cascade="all, delete")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Metóda na overenie hesla
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Idea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    #category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='idea', lazy=True, cascade="all, delete")
    upvotes = db.Column(db.Integer, default=0)
    categories = db.Column(db.String(255), nullable=True)
    image = db.Column(db.String(255), nullable=True)  # Tu bude cesta k obrázku
    working_users = db.relationship('User', secondary=working_on, backref=db.backref('working_ideas', lazy='dynamic'))
    completed_by = db.Column(db.String(255), nullable=True)  # Uloží ID používateľov ako CSV
    completion_link = db.Column(db.String(255), nullable=True)  # Link na hotový projekt
    completed_ideas = db.relationship('CompletedIdea', back_populates='idea', lazy=True, cascade="all, delete")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    idea_id = db.Column(db.Integer, db.ForeignKey('idea.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    

class Upvote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    idea_id = db.Column(db.Integer, db.ForeignKey('idea.id'), nullable=False)
    # Unikátna kombinácia užívateľ & nápad – zabráni duplikátnemu hlasovaniu
    __table_args__ = (db.UniqueConstraint('user_id', 'idea_id', name='unique_user_idea'),)

class CompletedIdea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    idea_id = db.Column(db.Integer, db.ForeignKey('idea.id'), nullable=False)
    completion_link = db.Column(db.String(255), nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='completed_ideas')
    idea = db.relationship('Idea', back_populates='completed_ideas')  # Opravený vzťah


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


# Routes
@app.route('/')
def home():
    categories = Category.query.all()
    selected_category = request.args.get('category')
    search_query = request.args.get('search', '')

    if selected_category:
        ideas = Idea.query.filter(Idea.categories.contains(selected_category))
    else:
        ideas = Idea.query

    if search_query:
        ideas = ideas.filter(Idea.title.contains(search_query) | Idea.description.contains(search_query))

    ideas = ideas.all()
    return render_template('index.html', ideas=ideas, categories=categories, selected_category=selected_category)






@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Skontrolujeme, či užívateľ už existuje
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Používateľské meno už existuje!', 'danger')
            return redirect(url_for('register'))

        # Vytvoríme nového používateľa a nastavíme hashované heslo
        user = User(username=username)
        user.set_password(password)  # Používame našu metódu na hashovanie hesla

        db.session.add(user)
        db.session.commit()
        flash('Registrácia úspešná! Teraz sa môžete prihlásiť.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):  # Overenie hashovaného hesla
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            session['is_category_admin'] = user.is_category_admin
            flash('Úspešné prihlásenie!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Nesprávne používateľské meno alebo heslo!', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/add_idea', methods=['GET', 'POST'])
def add_idea():
    if 'user_id' not in session:
        flash('Musíš byť prihlásený na pridanie nápadu.', 'danger')
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

        # Uloží kategórie ako reťazec oddelený čiarkami
        new_idea = Idea(title=title, description=description, user_id=user_id, categories=",".join(selected_categories), image=image_path)

        db.session.add(new_idea)
        db.session.commit()
        return redirect(url_for('home'))

    # Načíta aktuálne kategórie z databázy
    categories = Category.query.all()
    return render_template('add_idea.html', categories=categories)


@app.route('/admin')
def admin():
    if 'user_id' not in session:
        flash("Musíš byť prihlásený ako admin!", "danger")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if not user or not user.is_admin:
        flash("Nemáš oprávnenie na správu kategórií!", "danger")
        return redirect(url_for('home'))

    users = User.query.all()  # Načítanie všetkých používateľov
    ideas = Idea.query.all()  # Načítanie všetkých nápadov

    return render_template('admin.html', users=users, ideas=ideas)

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
    completed_user_ids = [completion.user_id for completion in idea.completed_ideas]
    return render_template('idea_detail.html', idea=idea, comments=comments, completed_user_ids=completed_user_ids)


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






@app.route('/idea/<int:idea_id>/complete', methods=['POST'])
def complete_idea(idea_id):
    if 'user_id' not in session:
        flash('Musíš sa prihlásiť, aby si mohol označiť nápad ako dokončený.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    idea = Idea.query.get_or_404(idea_id)
    completion_link = request.form.get('completion_link', '').strip()

    # Skontroluj, či už tento používateľ označil nápad ako dokončený
    existing_completion = CompletedIdea.query.filter_by(user_id=user_id, idea_id=idea_id).first()

    if not existing_completion:
        completed_idea = CompletedIdea(user_id=user_id, idea_id=idea_id, completion_link=completion_link)
        db.session.add(completed_idea)

        # ⚡ Odstránenie používateľa z "pracujem na tom"
        if user_id in [user.id for user in idea.working_users]:
            idea.working_users.remove(User.query.get(user_id))
            flash('Už viac nepracuješ na tomto nápade.', 'info')

        db.session.commit()
        flash('Úspešne si označil nápad ako dokončený!', 'success')
    else:
        flash('Tento nápad už máš označený ako dokončený.', 'warning')

    return redirect(url_for('idea_detail', idea_id=idea_id))


@app.route('/admin/block_user/<int:user_id>')
def block_user(user_id):
    if 'user_id' not in session:
        flash("Musíš byť prihlásený ako admin!", "danger")
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        user.is_blocked = True
        db.session.commit()
        flash(f"Používateľ {user.username} bol zablokovaný.", "warning")
    
    return redirect(url_for('admin'))

@app.route('/admin/unblock_user/<int:user_id>')
def unblock_user(user_id):
    if 'user_id' not in session:
        flash("Musíš byť prihlásený ako admin!", "danger")
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        user.is_blocked = False
        db.session.commit()
        flash(f"Používateľ {user.username} bol odblokovaný.", "success")
    
    return redirect(url_for('admin'))




@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session:
        flash("Musíš byť prihlásený ako admin!", "danger")
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)

    # Zabraňujeme adminovi, aby zmazal sám seba
    if user.id == session['user_id']:
        flash("Nemôžeš zmazať sám seba!", "danger")
        return redirect(url_for('admin'))

    db.session.delete(user)
    db.session.commit()
    flash("Používateľ bol odstránený.", "success")
    return redirect(url_for('admin'))




@app.route('/admin/categories', methods=['GET', 'POST'])
def manage_categories():
    if 'user_id' not in session:
        flash("Musíš byť prihlásený!", "danger")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Skontrolujeme, či je používateľ category_admin, ak nie, presmerujeme ho
    if not user or not user.is_category_admin:
        flash("Nemáš oprávnenie na správu kategórií!", "danger")
        return redirect(url_for('home'))  # Pošleme ho na hlavnú stránku

    if request.method == 'POST':
        category_name = request.form['category_name'].strip()
        if category_name:
            existing_category = Category.query.filter_by(name=category_name).first()
            if not existing_category:
                new_category = Category(name=category_name)
                db.session.add(new_category)
                db.session.commit()
                flash(f'Kategória "{category_name}" bola pridaná.', 'success')
            else:
                flash("Táto kategória už existuje!", 'warning')

    categories = Category.query.all()
    return render_template('admin_categories.html', categories=categories)


@app.route('/admin/delete_category/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    if 'user_id' not in session:
        flash("Musíš byť prihlásený!", "danger")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Ochrana: Len category_admin môže mazať kategórie
    if not user or not user.is_category_admin:
        flash("Nemáš oprávnenie odstraňovať kategórie!", "danger")
        return redirect(url_for('home'))

    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash("Kategória bola odstránená.", "success")
    return redirect(url_for('manage_categories'))


@app.route('/delete_own_idea/<int:idea_id>', methods=['POST'])
def delete_own_idea(idea_id):
    if 'user_id' not in session:
        flash("Musíte byť prihlásený!", "danger")
        return redirect(url_for('login'))

    idea = Idea.query.get_or_404(idea_id)

    # Skontrolujeme, či používateľ vlastní nápad
    if session['user_id'] != idea.user_id:
        flash("Nemôžete zmazať nápad, ktorý vám nepatrí!", "danger")
        return redirect(url_for('home'))

    # Zmažeme nápad aj s komentármi
    Comment.query.filter_by(idea_id=idea.id).delete()
    db.session.delete(idea)
    db.session.commit()
    
    flash("Váš nápad bol úspešne zmazaný!", "success")
    return redirect(url_for('home'))

@app.route('/edit_own_idea/<int:idea_id>', methods=['GET', 'POST'])
def edit_own_idea(idea_id):
    if 'user_id' not in session:
        flash("Musíte byť prihlásený!", "danger")
        return redirect(url_for('login'))

    idea = Idea.query.get_or_404(idea_id)

    # Skontrolujeme, či používateľ je vlastníkom nápadu
    if session['user_id'] != idea.user_id:
        flash("Nemôžete upraviť nápad, ktorý vám nepatrí!", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        idea.title = request.form['title']
        idea.description = request.form['description']
        selected_categories = request.form.getlist('categories')
        
        # Aktualizácia kategórií
        idea.categories = ",".join(selected_categories)

        db.session.commit()
        flash("Nápad bol úspešne upravený!", "success")
        return redirect(url_for('idea_detail', idea_id=idea.id))

    categories = Category.query.all()
    return render_template('edit_idea.html', idea=idea, categories=categories)


@app.route('/idea/<int:idea_id>/remove_completion', methods=['POST'])
def remove_completion(idea_id):
    if 'user_id' not in session:
        flash('Musíte byť prihlásený na zrušenie dokončenia nápadu.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    completed_idea = CompletedIdea.query.filter_by(user_id=user_id, idea_id=idea_id).first()

    if completed_idea:
        db.session.delete(completed_idea)
        db.session.commit()
        flash('Zrušili ste dokončenie nápadu.', 'success')
    else:
        flash('Nemôžete zrušiť dokončenie, pretože ste ho neoznačili ako dokončené.', 'warning')

    return redirect(url_for('idea_detail', idea_id=idea_id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    


