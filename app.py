from operator import add
import os
from re import A
import secrets
from flask import Flask, render_template, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_user import login_required, roles_required, UserManager, UserMixin, user_manager, current_user, SQLAlchemyAdapter
from flask_user.forms import RegisterForm
from flask_wtf import FlaskForm, file
from wtforms import  SelectField, IntegerField, StringField, FileField, validators
from wtforms.validators import ValidationError
from datetime import date, datetime

from wtforms.fields.simple import SubmitField, TextAreaField, TextField

app = Flask(__name__)

app.config['SECRET_KEY'] = 'thisisasecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['CSRF_ENABLED'] = True

# Flask-Mail SMTP server settings
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 465
# app.config['MAIL_USE_SSL'] = True
# app.config['MAIL_USE_TLS'] = False
# app.config['MAIL_USERNAME'] =  "reminderquipo@gmail.com"
# app.config['MAIL_PASSWORD'] = "reminderquipo123"
# app.config['MAIL_DEFAULT_SENDER'] = '"Project Green" <remiderquipo@gmail.com>'

# Flask-User settings 
app.config['USER_ENABLE_EMAIL'] = False
app.config['USER_APP_NAME'] = "Project Green"      # Shown in and email templates and page footers
app.config['USER_LOGIN_TEMPLATE'] = 'login.html'
app.config['USER_REGISTER_TEMPLATE'] = 'signup.html'
app.config['USER_AFTER_LOGOUT_ENDPOINT'] = 'index'
app.config['USER_AFTER_REGISTER_ENDPOINT'] = 'user.login'

app.config['USER_ALLOW_LOGIN_WITHOUT_CONFIRMED_EMAIL'] = True
app.config['USER_ENABLE_CONFIRM_EMAIL'] = False

db = SQLAlchemy(app)


# Tables

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(50), nullable = False, unique = True)
    # email = db.Column(db.String(255, collation='NOCASE'), nullable=False, unique=True)
    # email_confirmed_at = db.Column(db.DateTime())
    password = db.Column(db.String(255), nullable = False, server_default = '')
    active = db.Column(db.Boolean(), nullable = False, server_default = '0')

    # attributes for project green
    city = db.Column(db.String(255), nullable=False, default='')
    age = db.Column(db.Integer(), nullable=False, default=0)
    gender = db.Column(db.String(50), nullable=False, default='Female')
    institution = db.Column(db.String(200))
    points = db.Column(db.Integer, nullable=False, default=0)
    trees_planted = db.Column(db.Integer, nullable=False, default=0)


    roles = db.relationship('Role', secondary='user_roles')
    campaigns = db.relationship('Campaign', backref='organizer', lazy=True)
    images = db.relationship('Image', backref='uploader', lazy=True)
    sellers = db.relationship('Seller', backref='organizer', lazy=True)

    def __repr__(self) -> str:
        return f'name: {self.username}, city: {self.city}'


class Image(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), nullable=False, default='sapling.jpg')
    user = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)

class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.Integer(), primary_key=True)
    city_name = db.Column(db.String(50), nullable=False, unique=True)
    city_pincode = db.Column(db.Integer(), nullable=False)

class Campaign(db.Model):
    __tablename__ = 'campaigns' 
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    city = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text(), nullable=False)
    target = db.Column(db.Integer(), nullable=False)
    trees_planted = db.Column(db.Integer(), nullable=False, default=0)
    date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text(), nullable=False, default="")
    organizer_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    image_file = db.Column(db.String(50), nullable=False, default='default_campaign.jpg')
    last_maintenance = db.Column(db.DateTime())

    volunteers = db.relationship('User', secondary='campaign_volunteers')

class CampaignVolunteers(db.Model):
    __tablename__ = 'campaign_volunteers'
    id = db.Column(db.Integer(), primary_key=True)
    campaign_id = db.Column(db.Integer(), db.ForeignKey('campaigns.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id'))

class Seller(db.Model):
    __tablename__ = 'sellers'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    shop_name = db.Column(db.String(100), nullable=False, default='')
    city = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text(), nullable=False)
    contact_no = db.Column(db.String(20))
    image_file = db.Column(db.String(50), nullable=False, default='default_campaign.jpg')
    organizer_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)

# forms

class MyRegisterForm(RegisterForm):
    # cities = [city.city_name for city in  City.query.all()]
    city = SelectField('Choose your City', choices = ['Patna', 'Gorakhpur', 'Sagar'], validators=[validators.DataRequired()])
    age = IntegerField(validators=[validators.DataRequired()])
    gender = SelectField('Choose your Gender', choices = ['Female', 'Male'], validators=[validators.DataRequired()])
    institution = StringField()

class PlantTreeForm(FlaskForm):
    plant_image = FileField('Upload a selfie with your sapling', validators=[validators.DataRequired()])
    submit = SubmitField()

class WaterTreeForm(FlaskForm):
    your_image = FileField('Upload a selfie', validators=[validators.DataRequired()])
    submit = SubmitField()

class BecomeOrganizerForm(FlaskForm):
    submit = SubmitField()

class CreateCampaignForm(FlaskForm):
    name = StringField(validators=[validators.DataRequired()])
    address = StringField(validators=[validators.DataRequired()])
    target = IntegerField(validators=[validators.DataRequired()])
    # city = SelectField(choices=['Sagar', 'Patna'], validators=[validators.DataRequired()])
    image = FileField()
    description = TextAreaField(validators=[validators.DataRequired()])
    image_file = FileField('Campaign Image', validators=[file.FileRequired(), file.FileAllowed(['jpg', 'png'], 'Wrong Format')])
    submit = SubmitField()

class AddSellerForm(FlaskForm):
    name = StringField(validators=[validators.DataRequired()])
    shop_name = StringField(validators=[validators.DataRequired()])
    address = TextField(validators=[validators.DataRequired()])
    contact_no = StringField(validators=[validators.DataRequired()])
    image_file = FileField('Seller Image', validators=[file.FileRequired(), file.FileAllowed(['jpg', 'png'], 'Wrong Format')])
    submit = SubmitField()
    city = SelectField(choices=['Patna', 'Gorakhpur', 'Sagar'])

class SearchCityForm(FlaskForm):
    city = SelectField('Choose a City', choices=['Patna', 'Gorakhpur', 'Sagar'])
    submit = SubmitField('Search')

class DeleteSellerForm(FlaskForm):
    submit = SubmitField('Delete')

class EditSellerForm(FlaskForm):
    contact_no = StringField()
    address = TextField()
    submit = SubmitField('Update')

# user manager

class CustomUserManager(UserManager):

    def customize(self, app):
        self.RegisterFormClass = MyRegisterForm
    
    def password_validator(self, form, field):
        if len(field.data) < 6:
            raise ValidationError('Password should be atleast 6 characters long') 

# class DetailsForm(FlaskForm):
#     # cities = [city.city_name for city in  City.query.all()]
#     city = SelectField('Choose your city', choices = ['Sagar', 'Patna'], validators=[validators.DataRequired()])
#     age = IntegerField()
#     gender = SelectField('Choose your gender', choices = ['Male', 'Female'])
#     institution = StringField()


user_manager = CustomUserManager(app, db, User)


# app

@app.route('/', methods=['GET', 'POST'])
def index():
    if(current_user.is_authenticated):
        form = SearchCityForm()
        if(form.validate_on_submit()):
            return render_template('user_home.html', user = current_user, campaigns = Campaign.query.filter_by(city=form.city.data), city=form.city.data, form=form)
        return render_template('user_home.html', user = current_user, campaigns = Campaign.query.filter_by(city=current_user.city), form=form)
    else:
        return render_template('homepage.html')

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/images', picture_fn)
    form_picture.save(picture_path)
    return picture_fn


@app.route('/details/<campaign_id>', methods=['GET', 'POST'])
@login_required
def campaignDetail(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    form_tree = PlantTreeForm()
    form_water = WaterTreeForm()
    if form_tree.validate_on_submit():
        picture_file = save_picture(form_tree.plant_image.data)
        current_user.images.append(Image(name=picture_file))
        current_user.trees_planted = current_user.trees_planted + 1
        current_user.points = current_user.points + 10
        campaign.trees_planted = campaign.trees_planted + 1
        print(campaign.trees_planted)
        db.session.commit()
        flash("Congratulations!!! You Have Planted A Tree And Gained 10 Points", category="tree")
        return render_template('campaignDetail.html', campaign = campaign, form_tree = form_tree, form_water=form_water, tree = True, user=current_user)
    if form_water.validate_on_submit():
        picture_file = save_picture(form_water.your_image.data)
        current_user.images.append(Image(name=picture_file))
        current_user.points = current_user.points + 10
        campaign.last_maintenance = datetime.utcnow()
        db.session.add(campaign)
        db.session.commit()
        flash("Congratulations!!! You Took Care Of The Plants", category="water")
        return render_template('campaignDetail.html', campaign = campaign, form_tree = form_tree, form_water=form_water, water = True, user=current_user)


    return render_template('campaignDetail.html', campaign = campaign, form_tree = form_tree, form_water=form_water, user=current_user)

@app.route('/myprofile', methods=['GET', 'POST'])
@login_required
def userProfile():
    form = BecomeOrganizerForm()
    campaigns_in_city = len(Campaign.query.filter_by(city=current_user.city).all())
    percent = f'{int(((current_user.points)/200)*100)}%' 
    if form.validate_on_submit():
        current_user.roles.append(Role.query.first())
        db.session.commit()
        return render_template('user_profile.html', user = current_user, no_of_campaigns = campaigns_in_city, percent=percent, form=form)
    return render_template('user_profile.html', user = current_user, no_of_campaigns = campaigns_in_city, percent=percent, form=form)


@app.route('/create-campaign', methods=['GET', 'POST'])
@roles_required('Organizer')
def createCampaign():
    form = CreateCampaignForm()
    if form.validate_on_submit():
        name = form.name.data
        address = form.address.data
        target = form.target.data    
        city = current_user.city
        description = form.description.data
        if form.image_file.data.filename != '':
            image_file = save_picture(form.image_file.data)
        else:
            image_file = 'default_campaign.jpg'
        new_campaign = Campaign(name = name, city = city, address = address, target = target, description=description, image_file=image_file)
        current_user.campaigns.append(new_campaign)
        db.session.add(new_campaign)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('createCamp.html', form = form, user=current_user)

@app.route('/local-sellers')
@login_required
def localSellers():
    sellers = Seller.query.filter_by(city=current_user.city)
    if sellers.count() > 0:
        return render_template('localseller.html', user = current_user, sellers=sellers)
    else:
        return render_template('localseller.html', user = current_user)

@app.route('/about-us')
@login_required
def aboutUs():
    return render_template('aboutUs.html', user=current_user)

@app.route('/educate-yourself')
def educateYourself():
    return render_template('educateYourself.html', user=current_user)

@app.route('/add-seller', methods=['GET', 'POST'])
@roles_required('Organizer')
def addSeller():
    form = AddSellerForm()
    if form.validate_on_submit():
        name = form.name.data
        shop_name = form.shop_name.data
        address = form.address.data
        contact_no = form.contact_no.data
        city = form.city.data
        if form.image_file.data.filename != '':
            image_file = save_picture(form.image_file.data)
        else:
            image_file = 'default_campaign.jpg'
        new_seller = Seller(name=name, shop_name=shop_name, address=address, contact_no=contact_no, city=city, image_file=image_file, organizer_id=current_user.id)
        db.session.add(new_seller)
        db.session.commit()
        return redirect(url_for('manageSellers'))
    return render_template('add_sellers.html', user=current_user, form=form)

@app.route('/manage-sellers')
@roles_required('Organizer')
def manageSellers():
    return render_template('manageSellers.html', user=current_user)

@app.route('/manage-sellers/delete/<seller_id>', methods=['GET', 'POST'])
@roles_required('Organizer')
def deleteSeller(seller_id):
    form = DeleteSellerForm()
    seller = Seller.query.filter_by(id=seller_id).first()
    if form.validate_on_submit():
        db.session.delete(seller)
        db.session.commit()
        return redirect(url_for('manageSellers'))
    return render_template('manageSellers.html', user=current_user, delete=seller, form=form)

@app.route('/manage-sellers/edit/<seller_id>', methods=['GET', 'POST'])
@roles_required('Organizer')
def editSeller(seller_id):
    form = EditSellerForm()
    seller = Seller.query.filter_by(id=seller_id).first()
    if form.validate_on_submit():
        print(form.contact_no.data)
        seller.contact_no = form.contact_no.data
        seller.address = form.address.data
        print(seller.contact_no)
        db.session.commit()
        return redirect(url_for('manageSellers'))
    form.contact_no.data = seller.contact_no
    form.address.data = seller.address
    return render_template('manageSellers.html', user=current_user, edit=seller, form=form)

if __name__ == '__main__':
    app.run(debug=True)   