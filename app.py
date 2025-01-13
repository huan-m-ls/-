#encoding='utf-8'
#导入所需模块
import os
import random
from flask import Flask, render_template, redirect, url_for, flash, abort, session, request, jsonify, send_from_directory
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, ValidationError, RadioField
from wtforms.validators import Email, DataRequired, Length, EqualTo
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from threading import Thread
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

#创建应用实例
app = Flask(__name__)

#配置表单密令
SECRET_KEY='\xfe{\xa9\n\x1b0\x16\xcfF\xb103\x9d)\xdf\xfd\xab\xd8\x9b\xbf\xf2\xf5\xb0\x86'

#数据库配置
basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')	#数据库URI		
SQLALCHEMY_COMMIT_ON_TEARDOWN = True	#更改自动提交
SQLALCHEMY_TRACK_MODIFICATIONS = True

#应用配置
app.config.from_object(__name__)

#实例化所需模块
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
manager = Manager(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

#管理员表单模型
class AdminForm(FlaskForm):
	#邮箱验证
	def account_check(self, field):
		if field.data != '2879858249@qq.com':
			raise ValidationError('你可能是假的管理员')
	#密码验证
	def password_check(self, field):
		if field.data != '2879858249':
			raise ValidationError('你可能是假的管理员')

	email = StringField("管理员邮箱", validators=[DataRequired(message='邮箱是空的请加油'), 
		Email(message=u'不是邮箱'), account_check])
	password = PasswordField("管理员密码", validators=[DataRequired(message='密码忘了哦'), password_check])
	login = SubmitField("有请最牛逼的管理员登录")

#管理员增加用户表单模型
class AdminAddForm(FlaskForm):
	#检测邮箱唯一性
	def email_unique(self, field):
		if User.query.filter_by(email=field.data).first():
			raise ValidationError('邮箱存在')

	name = StringField('用户名', validators=[DataRequired()])
	email = StringField('用户邮箱', validators=[DataRequired(), email_unique])
	password = StringField('用户密码', validators=[DataRequired()])
	role = RadioField('身份', choices=[('学生', '学生'), ('教师', '教师')], default='学生')
	add = SubmitField("增加用户")
			
#用户登录表单模型
class LoginForm(FlaskForm):
	#验证用户是否存在
	def email_exist(self, field):
		if not User.query.filter_by(email=field.data).first():
			raise ValidationError('邮箱格式错误')
	
	email = StringField("邮箱", validators=[DataRequired(message='邮箱为空'), 
		Email(message=u'邮箱不能为空'), email_exist])
	password = PasswordField("密码", validators=[DataRequired(message='必须填入密码')])
	login = SubmitField("登录")

#用户注册表单模型
class SignupForm(FlaskForm):
	def email_unique(self, field):
		if User.query.filter_by(email=field.data).first():
			raise ValidationError('该邮箱已被注册')
	#检测密码中是否有空格
	def password_noblank(self, field):
		for s in field.data:
			if s == ' ':
				raise ValidationError('密码中不能含有空格')

	name = StringField('姓名', validators=[DataRequired(message='必填')])
	email = StringField("邮箱", validators=[DataRequired(message='邮箱不能为空'), 
		Email(message='邮箱错误'), email_unique])
	password = PasswordField("密码", validators=[DataRequired(message='密码不能为空'),
		Length(6, message='密码过短,请大于6位'), password_noblank])		
	confirm = PasswordField("确认密码", validators=[DataRequired(message='请注意确认正确'),
		EqualTo('password', "两次密码不一样!")])
	role = RadioField('身份', choices=[('学生', '学生'), ('教师', '教师')], default='教师')
	signup = SubmitField("注册")

#找回密码表单模型
class ResetPasswordForm(FlaskForm):
	email = StringField(
		'邮箱',
		validators=[
			DataRequired(message="邮箱不能为空"),
			Email(message="邮箱格式不正确")
		]
	)
	password = PasswordField(
        '新密码',
        validators=[
            DataRequired(message="密码不能为空"),
            Length(min=6, max=20, message="密码长度需在6到20个字符之间")
        ]
    )
	confirm_password = PasswordField(
        '确认密码',
        validators=[
            DataRequired(message="请再次输入密码"),
            EqualTo('password', message="两次输入的密码不一致")
        ]
    )
	submit = SubmitField('提交')

#教师新增学生表单模型
class AddForm(FlaskForm):
	#检测学号是否存在
	def student_exist(self, field):
		user = User.query.filter_by(id=session.get('user_id')).first()
		for student in user.students:
			if student.stu_id == field.data:
				raise ValidationError("该学号学生已存在")

	stu_id = StringField("学生学号", validators=[DataRequired(message="不能为空"), Length(6, 15, "有点短?有点长?"), student_exist])
	name = StringField("学生姓名", validators=[DataRequired(message="不能为空"), Length(-1, 10, "名字过长")])
	cls = StringField("专业班级", validators=[DataRequired(message="不能为空"), Length(-1, 15, "超长")])
	addr = StringField("所在寝室", validators=[DataRequired(message="不能为空"), Length(-1, 15, "超长")])
	phone = StringField("联系方式", validators=[DataRequired(message="不能为空")])
	add = SubmitField("添加")

#教师搜索学生表单模型
class SearchForm(FlaskForm):
	keyword = StringField("输入查询关键字", validators=[DataRequired(message="输入不能为空")])
	search = SubmitField("Find It!")
		
#用户模型
class User(db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64))
	email = db.Column(db.String(64), index=True, unique=True)
	password = db.Column(db.String(64))
	#身份
	role = db.Column(db.String(64), default='学生')
	#激活状态
	active_state = db.Column(db.Boolean, default=True)
	#随机码
	active_code = db.Column(db.String(10))
	#所管理的学生
	students = db.relationship('Student', backref='user', lazy='dynamic')
	#冻结状态
	frozen = db.Column(db.Boolean, default=False)

#学生模型
class Student(db.Model):
	__tablename__ = 'students'
	id = db.Column(db.Integer, primary_key=True)
	stu_id = db.Column(db.String(64), index=True)
	name = db.Column(db.String(64))
	#班级
	cls = db.Column(db.String(64))
	#寝室
	addr = db.Column(db.String(64))
	phone = db.Column(db.String(64))
	#教师id
	user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

#初始化数据库
db.create_all()

#登录路由控制
@app.route('/', methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		#验证是否被冻结
		if user.frozen:
			flash("你的账户已被冻结")
			return redirect(url_for('login'))
		#验证密码是否正确
		elif user.password != form.password.data:
			flash("密码不正确")
			return redirect(url_for('login'))
		#记住登录状态
		session['user_id'] = user.id
		#根据身份重定向
		if user.role == '教师':
			return redirect('/u/' + str(user.id))
		if user.role == '学生':
			return redirect('/s/' + str(user.id))
	return render_template('form.html', form=form)

#退出路由控制
@app.route('/logout')
def logout():
	#管理员退出
	if session.get('admin'):
		session['admin'] = None
	#普通用户退出
	elif session.get('user_id') is None:
		flash("未登录")
		return redirect(url_for('login'))
	flash("退出成功")
	session['user_id'] = None
	return redirect(url_for('login'))

#注册路由控制
@app.route('/signup', methods=['GET', 'POST'])
def signup():
	form = SignupForm()
	if form.validate_on_submit():
		#生成随机码
		n = []
		for i in range(10):
			n.append(str(random.randint(0, 9)))
		active_code = ''.join(n)
		#实例化用户
		new_user = User(name=form.name.data, email=form.email.data, password=form.password.data,
			role=form.role.data, active_code=active_code)
		#新增用户
		db.session.add(new_user)

		return redirect(url_for('login'))
	return render_template('form.html', form=form)

# 找回密码路由控制
@app.route('/forget', methods=['GET', 'POST'])
def forget():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # 验证邮箱是否存在
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # 验证通过，直接跳转到设置新密码页面
            return redirect(url_for('reset_password', user_id=user.id))
        else:
            flash("该邮箱未注册")
            return redirect(url_for('forget'))
    return render_template("form.html", form=form)

# 设置新密码路由控制
@app.route('/reset_password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
	form = ResetPasswordForm()  # 自定义表单，包含新密码字段
	user = User.query.get(user_id)
	if not user:
		abort(404)  # 用户不存在

	if form.validate_on_submit():
        # 更新密码并存入数据库
		user.password = form.password.data
		db.session.commit()
		flash("密码已成功更新，请重新登录")
		return redirect(url_for('login'))

	return render_template("form.html", form=form)


#教师主页路由控制
@app.route('/u/<int:id>')
def user(id):
	#验证是否已登录
	if session.get('user_id') is None or id != session.get('user_id'):
		session['user_id'] = None
		flash("未登录")
		return redirect(url_for('login'))
	user = User.query.filter_by(id=id).first()
	#验证身份
	if user.role != '教师':
		abort(400);
	return render_template('user.html', user=user)

#学生主页路由控制
@app.route('/s/<int:id>')
def student(id):
	if session.get('user_id') is None or id != session.get('user_id'):
		session['user_id'] = None
		flash("未登录")
		return redirect(url_for('login'))
	user = User.query.filter_by(id=id).first()
	teachers = User.query.filter_by(role='教师').all()
	if user.role != '学生':
		abort(400);
	return render_template('student.html', user=user, teachers=teachers)

#账户信息路由控制
@app.route('/u/<int:id>/account')
def account(id):
	if session.get('user_id') is None or id != session.get('user_id'):
		session['user_id'] = None
		flash("未登录")
		return redirect(url_for('login'))
	user = User.query.filter_by(id=id).first()
	num = user.students.count()
	return render_template('account.html', user=user, num=num)

#学生选择教师路由控制
@app.route('/s/<int:user_id>/<int:teacher_id>')
def detail(user_id, teacher_id):
	if session.get('user_id') is None or user_id != session.get('user_id'):
		session['user_id'] = None
		flash("未登录")
		return redirect(url_for('login'))
	user = User.query.filter_by(id=user_id).first()
	if user.role != '学生':
		abort(400);
	teacher = User.query.filter_by(id=teacher_id).first()
	#为了更改id和role重新构建用户传递给跳转页面
	x_user = {}
	x_user['id'] = user_id
	x_user['role'] = '学生'
	x_user['name'] = teacher.name
	x_user['students'] = teacher.students
	return render_template('detail.html', user=x_user)

#教师新增学生路由控制
@app.route('/u/<int:id>/add', methods=['GET', 'POST'])
def add(id):
	if session.get('user_id') is None or id != session.get('user_id'):
		session['user_id'] = None
		flash("未登录")
		return redirect(url_for('login'))
	user = User.query.filter_by(id=id).first()
	if user.role != '教师':
		abort(400);
	form = AddForm()
	if form.validate_on_submit():
		#构建新学生并保存
		new_student = Student(stu_id=form.stu_id.data, name=form.name.data,
			cls=form.cls.data, addr=form.addr.data, phone=form.phone.data, user_id=id)
		db.session.add(new_student)
		flash("添加成功")
		return redirect('/u/' + str(id) + '/add')	
	return render_template('form.html', form=form, user=user)

#教师搜索学生路由控制
@app.route('/u/<int:id>/search', methods=['GET', 'POST'])
def search(id):
	if session.get('user_id') is None or id != session.get('user_id'):
		session['user_id'] = None
		flash("未登录")
		return redirect(url_for('login'))
	form = SearchForm()
	user = User.query.filter_by(id=id).first()
	if user.role != '教师':
		abort(400);

	hide = set()	#不需显示的学生集合
	if form.validate_on_submit():
		for student in user.students:
			word = str(student.stu_id) + ' ' + student.name + ' ' + student.cls + ' ' + \
				student.addr + ' ' + student.phone
			#没有关键字则添加进hide集合
			if form.keyword.data not in word:
				hide.add(student)
	return render_template('form.html', form=form, search=True, user=user, hide=hide)

#教师删除学生路由控制
@app.route('/u/<int:id>/delete', methods=['POST'])
def delete(id):
	if session.get('user_id') is None or id != session.get('user_id'):
		session['user_id'] = None
		flash("未登录")
		return redirect(url_for('login'))
	user = User.query.filter_by(id=id).first()
	if user.role != '教师':
		abort(400);

	student = Student.query.filter_by(stu_id=request.form.get('stu_id'), user_id=id).first()
	if student:
		db.session.delete(student)
	return jsonify({'result': 'success'})

#教师更改学生路由控制
@app.route('/u/<int:id>/change', methods=['POST'])
def change(id):
	if session.get('user_id') is None or id != session.get('user_id'):
		session['user_id'] = None
		flash("未登录")
		return redirect(url_for('login'))
	user = User.query.filter_by(id=id).first()
	if user.role != '教师':
		abort(400);
	#更改学生信息
	student = Student.query.filter_by(id=request.form.get('id')).first()
	student.stu_id = request.form.get('stu_id')
	student.name = request.form.get('name')
	student.cls = request.form.get('cls')
	student.addr = request.form.get('addr')
	student.phone = request.form.get('phone')
	db.session.add(student)
	return jsonify({'result': 'success'})

#管理员登录路由控制
@app.route('/admin', methods=['GET', 'POST'])
def admin():
	form = AdminForm()
	if form.validate_on_submit():
		session['admin'] = True
		return redirect('/admin/control')
	return render_template('form.html', form=form)

#管理员控制台路由控制
@app.route('/admin/control', methods=['GET', 'POST'])
def control():
	if not session.get('admin'):
		abort(400)
	users = User.query.all()
	return render_template('control.html', users=users)

#管理员新增用户路由控制
@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add():
	if not session.get('admin'):
		abort(400)
	form = AdminAddForm()
	if form.validate_on_submit():
		#简化增加用户,自动生成随机码
		n = []
		for i in range(10):
			n.append(str(random.randint(0, 9)))
		active_code = ''.join(n)
		#自动构建通过验证的用户
		user = User(name=form.name.data, email=form.email.data, password=form.password.data,
			role=form.role.data, active_code=active_code, active_state=True)
		db.session.add(user)
		flash('增加成功')
		return redirect(url_for('admin_add'))
	return render_template('adminadd.html', form=form)

#管理员删除用户路由控制
@app.route('/admin/delete', methods=['POST'])
def admin_delete():
	if session.get('admin'):
		user = User.query.filter_by(id=request.form.get('id')).first()
		if user:
			db.session.delete(user)
		return 'ok'
	abort(400)

#管理员冻结用户路由控制
@app.route('/admin/frozen', methods=['POST'])
def admin_frozen():
	if session.get('admin'):
		user = User.query.filter_by(id=request.form.get('id')).first()
		if user:
			user.frozen = True
			db.session.add(user)
		return 'ok'
	abort(400)

#管理员解冻用户路由控制
@app.route('/admin/normal', methods=['POST'])
def admin_normal():
	if session.get('admin'):
		user = User.query.filter_by(id=request.form.get('id')).first()
		user.frozen = False
		db.session.add(user)
		return 'ok'
	abort(400)

#错误页面路由控制
@app.errorhandler(404)
def page_not_found(e):
	return render_template('error.html', code='404'), 404

@app.errorhandler(500)
def internal_server_error(e):
	return render_template('error.html', code='500'), 500

@app.errorhandler(400)
def bad_request(e):
	return render_template('error.html', code='400'), 500

#程序启动入口
if __name__ == '__main__':
	manager.run()
