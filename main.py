import code
from ssl import SSL_ERROR_SSL
from flask import Flask, render_template, request, redirect, url_for, flash, session 
import webbrowser

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user 
from werkzeug.security import generate_password_hash, check_password_hash
import etsyauth, googleauth, sheets, pinterestauth
from time import time
from config import access_key, database_url, pinterest_api_key, pinterest_secret_key


database_url = database_url.replace("postgres://", "postgresql://", 1)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']= database_url


callback_uri = "http://localhost:8080/home"

db=SQLAlchemy(app)

app.secret_key = "adspend1234"

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(30), unique=True)
    password = db.Column(db.String, unique=True)
    etsy_key = db.Column(db.String)
    etsy_secret = db.Column(db.String)
    spreadsheetId = db.Column(db.String, unique=True)
    pinterest_token= db.Column(db.String)
    pinterest_refresh = db.Column(db.String)
    

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.etsy_key = None
        self.etsy_secret = None
        self.spreadsheetId = None
        self.pinterest_token = None
        self.pinterest_refresh = None

#instantiating, intializing login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Create database 
db.create_all()
db.session.commit()


# OAuth Blueprints: 


@login_manager.user_loader
def load(user_id):
    return User.query.get(int(user_id))

# Debug ##
def getUserInfo(user):
    print("The current user's username: %s" % user.username)
    user = User.query.filter_by(username=user.username).first()
    print("Their spreadsheet ID: %s " % user.spreadsheetId)
    print("Their etsy key: %s" % user.etsy_key)


##### Routes #####
@app.route('/', methods = ['POST', 'GET'])
def index():
    if(current_user.is_authenticated):
        return redirect(url_for('home'))
    return render_template('index.html')


@app.route('/privacy', methods = ['GET'])
def privacy():

    return render_template('privacy.html')

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if(current_user.is_authenticated):
        return redirect(url_for("home"))
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        magic_code = request.form.get("magic_code")

        user=User.query.filter_by(username=username).first()

        if user:
            flash("A user with this username already exists!")
            return redirect(url_for('signup'))
        

        if (magic_code != access_key):
            flash("Invalid magic code!")
            return redirect(url_for('signup'))
        
        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        new_user=User.query.filter_by(username=username).first()
        login_user(new_user, remember=True)
        return redirect(url_for('home'))
    
     
    return render_template("signup.html")

@app.route('/login', methods = ['POST', 'GET'])
def login():

    if (current_user.is_authenticated == True):
        return redirect(request.referrer)

    if request.method == "POST":
        username=request.form.get("username")
        password = request.form.get("password")

        user=User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password, password):
            flash("Incorrect username or password!")
            return redirect(url_for('login'))
        else:
            login_user(user, remember=True)
            return redirect(url_for('home'))

    return render_template('login.html')
  
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('logout.html')

@app.route('/home', methods = ['POST', 'GET'])
@login_required
def home():

    user = User.query.filter_by(username=current_user.username).first()
    pinterest_redirect = False 
    google_redirect = False
    if request.args.get('state') == None and request.args.get('code') != None:
        pinterest_redirect = True
    
    if request.args.get('state') != None and request.args.get('code') != None:

        google_redirect = True
    
   # Pinterest Authentication
    if pinterest_redirect:
       pinterest_code = request.args.get('code')
       pinterestauth.fetchToken(pinterest_code, user)

    # Google Authentication
    elif google_redirect:
        google_code = request.args.get('code')
        if (google_code != None):
            googleauth.fetchToken(request.url, user, request.args.get('state'))


    # Etsy Authentication 
    hasEtsyKey = True if (user.etsy_key != None) else False
    etsy_code = request.args.get('oauth_verifier')

    if etsy_code != None and not hasEtsyKey:   
        etsyauth.fetchToken(etsy_code, current_user)
        return redirect(url_for('home'))

    token = session.get('google_token')
    hasGoogleToken = True if token != None else False
    sheet = url_for('getsheet') if hasGoogleToken else "#" 


    return render_template("home.html", etsy_key=hasEtsyKey,
                           google_access=request.url, google_token=hasGoogleToken, sheetlink=sheet)

@app.route('/getsheet', methods=['GET', 'POST'])
def getsheet():

    session.modified = True

    token = session.get('google_token')
    if (token == None):
        flash('Please authorize your Google account before proceeding.')
        return redirect(url_for('getsheet'))
        

    # Refresh the token when we hit the make another API call if it  fresh! 
    if (time() >= session['google_token_expir']):
        print(session['google_token_expir'])
        googleauth.refreshToken()
  
   

    # Get My Sheet! 
    user=User.query.filter_by(username=current_user.username).first()
    mySheetId = user.spreadsheetId 

    if (mySheetId== None):
        # if we don't have a recorded sheet, create a new one

        return redirect(sheets.createNewSheet())
    else:
        return redirect(sheets.updateSheet(mySheetId))
    
@app.route('/googlelogin', methods = ['GET'])
async def googlelogin():
        await googleauth.authorizeGoogle() # returns url 
        google_state = session["oauth_state"] 
        return redirect(session.get('google_url'))

@app.route('/etsylogin', methods=['GET'])
def etsylogin():
        etsyauth.authorizeEtsy()
        return redirect(session.get('etsy_url'))

@app.route('/pinterestlogin', methods=['GET'])
def pinterestlogin():
    return pinterest.authorize(callback=url_for('home'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)




