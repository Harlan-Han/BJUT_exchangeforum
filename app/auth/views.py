# This file is to write the route and some response to the user in different conditions
from flask import render_template, redirect, request, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, \
    current_user
from . import auth
from .. import db
from ..models import User, Students
from ..email import send_email
from .forms import  ChangePasswordForm,\
    PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm


# This method is used to update the last access time of the logged in user
@auth.before_app_request
def before_request():
    # 首先先判断该用户是否登录
    if current_user.is_authenticated:
        # 如果用户提供的登录凭据有效，调用models的ping()方法来刷新用户最后访问时间
        # current_user.ping()
        if not current_user.confirmed \
                and request.endpoint \
                and request.blueprint != 'auth' \
                and request.endpoint != 'static':
            # 如果用户提供的登录凭据无效，返回auth.unconfirmed界面
            return redirect(url_for('auth.unconfirmed'))


# 登录路由
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')
    if request.method == 'POST':
        #通过Ajax获取前端数据的方法
        # stuID = request.form.get('stuID')
        # pwd = request.form.get('password')
        student_id= request.form["user"]
        password = request.form["pwd"]
        user = User.query.filter_by(student_id=student_id).first()
        if user is None:
            flash("您的学号还没有注册")
            return render_template('auth/login.html')
        elif user.verify_password(password) is False :
            flash("用户名或密码错误")
            return render_template('auth/login.html')
        if user is not None and user.verify_password(password):
            login_user(user, True)
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('main.index')
            return redirect(next)
        return render_template('auth/login.html')


# 登出路由
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))


# 注册路由
@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('auth/register.html')
    if request.method == 'POST':
        # 读取前端的学号数据
        isstudent = Students.query.filter_by(student_id = request.form["BJUT_id"]).first()#学号
        if isstudent is None:
            flash("很抱歉，您不是BJUT的学生无法注册此账户")
            return render_template('auth/register.html')
        if isstudent.id_number != request.form["id_num"]:
            flash("您的学号与身份证号不匹配，无法注册此账户")
            return render_template('auth/register.html')
        if isstudent is not None and isstudent.id_number == request.form["id_num"]:
            if isstudent.confirmed == True:
                flash("您的学号已被注册，您无法注册第二个SOFB账户")
                return render_template('auth/register.html')
            else:
                emailfind = User.query.filter_by(email=request.form["email"]).first()
                if emailfind is not None:
                    flash("您的邮箱已被注册，请更换您的邮箱")
                    return render_template('auth/register.html')
                usernamefind = User.query.filter_by(username=request.form["user_name"]).first()
                if usernamefind is not None:
                    flash("您的用户名已被注册，请更换您的用户名")
                    return render_template('auth/register.html')
                user = User(email=request.form["email"],
                            ID_number=request.form["id_num"],
                            student_id=request.form["BJUT_id"],
                            username=request.form["user_name"],
                            password=request.form["confirm_pwd"])
                isstudent.confirmed = True
                db.session.add(isstudent)
                db.session.add(user)
                db.session.commit()
                #注册时发送邮箱认证
                token = user.generate_confirmation_token()
                send_email(user.email, 'Confirm Your Account',
                           'mail/confirm', user=user, token=token)
                flash('A confirmation email has been sent to you by email.',category='info')
                return redirect(url_for('auth.login'))
        return render_template('auth/register.html')


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'GET':
        return render_template('auth/change_password.html')
    if request.method == 'POST':
        old_password = request.form["old"]
        password = request.form["new1"]

        # password2 = request.form["new2"]
        # if(password != password2):这里需要test一下有没有这个验证

        if current_user.verify_password(old_password):
            current_user.password = password
            db.session.add(current_user)
            db.session.commit()
            flash('Your password has been updated.')
            return redirect(url_for('main.index'))
        else:
            # flash('Invalid password.')
            return "<h2>修改失败</h2>"





@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')




# 确认路由
@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))


# 再次发送邮箱
@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))





# 忘记密码时，发送邮件。
@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    # if not current_user.is_anonymous:
    #     return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password',
                       'mail/reset_pwd',
                       user=user, token=token)
        flash('An email with instructions to reset your password has been '
              'sent to you.')
        # return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


# 邮件里面的连接生成的修改密码的网页。
@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    # if not current_user.is_anonymous:
    #     return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        if User.reset_password(token, form.password.data):
            db.session.commit()
            flash('Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)





# 重置邮箱路由
@auth.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data.lower()
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, 'Confirm your email address',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('An email with instructions to confirm your new email '
                  'address has been sent to you.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template("auth/change_email.html", form=form)


# 修改邮箱
@auth.route('/change_email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        db.session.commit()
        flash('Your email address has been updated.')
    else:
        flash('Invalid request.')
    return redirect(url_for('main.index'))
