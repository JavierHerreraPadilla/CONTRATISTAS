import flask

from ingresos import app, db
from flask import session, abort, render_template, request, jsonify, redirect, url_for, flash
from .models import Client, Supplier, Worker, Job, JobWorker, ClientVenue, SupplierAssignedJobs
from .forms import LoginForm, RegisterForm, WorkerForm, JobForm, AssignedJobForm, MultipleJobForm
from flask_login import login_user, logout_user, login_required, current_user, LoginManager
import requests
from datetime import datetime, timedelta
import calendar
from .decorators import client_only, supplier_only

# ten en cuenta que se está logueando con base en el nit (login_user - user_loader)
# por lo que no puede haber un cliente que a la vez sea supplier porque entrarán en conflicto

### Sistema de loggeo
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(nit):
    client = Client.query.filter_by(nit=nit).first()
    supp = Supplier.query.filter_by(nit=nit).first()
    user = client or supp
    return user


### decorator client only


@app.route("/")
def home():
    log_form = LoginForm()
    reg_form = RegisterForm()
    if current_user.is_authenticated:
        return redirect(url_for('client_panel', user=current_user)) if isinstance(current_user, Client) else redirect(url_for('supp_panel', user=current_user))
    return render_template("home.html", log_form=log_form, reg_form=reg_form, user=current_user)


@app.route("/login", methods=["POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        client = db.session.query(Client).filter_by(nit=int(form.nit.data)).first()
        supplier = db.session.query(Supplier).filter_by(nit=int(form.nit.data)).first()
        user = client or supplier
        print(user)
        if not user:
            flash("Usuario no exite. Regístrate", "info")
            return redirect(url_for('home'))
        elif user.password != form.password.data:
            flash("Contraseña incorrecta", "info")
            return redirect(url_for('home'))
        else:
            login_user(user)
            if isinstance(user, Client):
                return redirect(url_for('client_panel', user=current_user))
            elif isinstance(user, Supplier):
                return redirect(url_for('supp_panel', user=current_user))


@app.route("/register", methods=["POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_client = Client(name=form.name.data,
                            nit=int(form.nit.data),
                            email=form.email.data,
                            password=form.password.data)
        db.session.add(new_client)
        db.session.commit()
        login_user(new_client)
        new_venue = ClientVenue(client_id=current_user.id)
        db.session.add(new_venue)
        db.session.commit()
        return redirect(url_for('client_panel', user=current_user))
    else:
        flash(f"{form.errors}", "danger")
        return redirect(url_for('register'))


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home', user=current_user))


@app.route("/client-panel")
@login_required
def client_panel():
    year = datetime.now().year
    month = datetime.now().month
    current_month = calendar.monthcalendar(year, month)
    client_suppliers = current_user.suppliers
    date = datetime.now().date()
    # todo mostrar los trabajos basado en la fecha - solo los del mes actual
    return render_template("client_panel.html",
                           current_month=current_month,
                           user=current_user,
                           supps=client_suppliers,
                           date=date)


@app.route("/supplier-panel")
@login_required
def supp_panel():
    return render_template("supp_panel.html", user=current_user)


@app.route("/suppliers/create-new", methods=["POST", "GET"])
@login_required
@client_only
def create_supplier():
    form = RegisterForm()
    if request.method == "POST":
        if form.validate_on_submit():
            new_supplier = Supplier(name=form.name.data,
                                    nit=int(form.nit.data),
                                    email=form.email.data,
                                    password=form.password.data,
                                    client_id=current_user.id
                                    )
            db.session.add(new_supplier)
            db.session.commit()
            flash("Proveedor creado exitosamente", "success")
            return redirect(url_for('create_supplier'))
    return render_template("create_supplier.html", form=form, user=current_user)


@app.route("/suppliers/list", methods=["POST", "GET"])
@login_required
@client_only
def supp_list():
    """Returns the list of suppliers for a given client"""
    suppliers = current_user.suppliers
    return render_template("suppliers_list.html", user=current_user, suppliers=suppliers)


@app.route("/change-satuts")
@login_required
@client_only
def change_status():
    """changes supplier status (active - inactive) """
    supp_id = int(request.args.get("supp_id"))
    supp = db.session.query(Supplier).filter_by(id=supp_id).first()
    supp.abled = bool(request.args.get("status"))
    db.session.commit()
    return redirect(url_for("supp_list", user=current_user))


@app.route("/admin-venues")
@login_required
@client_only
def admin_venues():
    return render_template('venues.html', user=current_user,
                           venues=current_user.venues
                           )


@app.route("/edit-venue", methods=["POST", "GET"])
@login_required
@client_only
def edit_venue():
    if request.method == "POST":
        venue_new_name = request.form.to_dict().get("venue_name")
        venue_id = int(request.form.to_dict().get("id"))
        venue = db.session.query(ClientVenue).filter_by(id=venue_id).first()
        venue.venue_name = venue_new_name
        db.session.commit()
    elif request.args.get("action"):
        db.session.add(
                        ClientVenue(venue_name=f"Sede {len(current_user.venues) + 1}",
                                      client_id=current_user.id)
                     )
        db.session.commit()
        return redirect(url_for("admin_venues"))

    else:
        if len(current_user.venues) == 1:
            flash("Hay una sola sede. No se puede eliminar", "info")
            return redirect(url_for("admin_venues", user=current_user))
        venue_id = int(request.args.to_dict().get("venue_id"))
        venue_to_remove = db.session.query(ClientVenue).filter_by(id=venue_id).first()
        db.session.delete(venue_to_remove)
        db.session.commit()
        flash("Sede eliminada", "success")
    return redirect(url_for("admin_venues", user=current_user))


@app.route("/assigned-tasks", methods=["POST", "GET"])
@login_required
@client_only
def edit_supp_tasks():
    form = AssignedJobForm()
    supp_name = db.session.query(Supplier).filter_by(id=int(request.args.get("supp_id"))).first().name
    # if int(request.args.get("user_id")) != current_user.id:
    #     return abort(403)
    if form.validate_on_submit():
        new_supp_job = SupplierAssignedJobs(description=form.description.data,
                                       supplier_id=form.supp_id.data,
                                       )
        db.session.add(new_supp_job)
        db.session.commit()
        flash("Tarea creada de forma correcta", "success")
        return redirect(url_for('supp_list', user=current_user))
    print(form.errors)
    return render_template("edit_supp_tasks.html", user=current_user,
                           form=form,
                           supp_id=int(request.args.get("supp_id")),
                           supp_name=supp_name,
                           )

@app.route("/delete-assigned-task")
@login_required
@client_only
def delete_assigned_task():
    """deletes am assigned task from a supplier"""
    assigned_task_id = int(request.args.get("task_id"))
    assigned_task_id_to_del = db.session.query(SupplierAssignedJobs).filter_by(id=assigned_task_id).first()
    db.session.delete(assigned_task_id_to_del)
    db.session.commit()
    flash("Tarea eliminada", "info")
    return redirect(url_for('supp_list', user=current_user))


@app.route("/register-worker", methods=["POST", "GET"])
@login_required
@supplier_only
def register_worker():
    """this route allows suppliers to create their workers"""
    session["workers_to_add"] = None  # esto es para borrar la lista de trabajadores añadadidos al momento de registrar una tarea
    form = WorkerForm()
    workers = current_user.workers
    if request.method == "POST" and form.validate_on_submit():
        form_data = dict(form.data)
        form_data.pop("submit")
        form_data.pop("csrf_token")
        new_worker = Worker(**form_data,
                            supplier_id=current_user.id
                            )
        db.session.add(new_worker)
        db.session.commit()
        return redirect(url_for('register_worker'))
    else:
        return render_template("register-worker.html", user=current_user, form=form,
                               workers=workers)



@app.route("/create-job", methods=["POST", "GET"])
@login_required
@supplier_only
def create_job():
    print("session in main", session.get("workers_to_add"))
    added_workers = list(enumerate([db.session.query(Worker).filter_by(id=worker_id[1]).first() for worker_id in session.get("workers_to_add")])) if session.get("workers_to_add") else None
    forms = MultipleJobForm(jobs=[{}] * len(added_workers)) if added_workers else None
    if added_workers:
        for form in forms._fields.get("jobs"):
            form.assigned_jobs.choices = [(job.id, job.description) for job in current_user.assigned_jobs]
            form.venue.choices = [(venue.id, venue.venue_name) for venue in current_user.client.venues] #list(enumerate(current_user.client.venues))
    workers = current_user.workers
    if request.method == "POST" and forms.validate_on_submit():
        print("validaron todas")
        print("++/+/+//+/", forms.data)
        # workers_id_list = [int(worker[1]) for worker in request.form.to_dict().items() if worker[0].startswith("worker")]
        # if len(workers_id_list) == 0:
        #     flash("Cada trabajo debe tener por lo menos un trabajador", "danger")
        #     return redirect(url_for('create_job'))
        # new_job = Job(title=form.title.data,
        #               description=form.assigned_jobs.data,
        #               start_date=form.start_date.data,
        #               end_date=form.end_date.data,
        #               supplier_id=current_user.id,
        #               client_venue_id=form.venue.data
        #               )
        # db.session.add(new_job)
        # db.session.commit()
        # for worker_id in workers_id_list:
        #     new_jobworker = JobWorker(job_id=new_job.id,
        #                               worker_id=worker_id)
        #     db.session.add(new_jobworker)
        #     db.session.commit()
        # flash("trabajo creado exitosamente", "success")
        # session["workers_to_add"] = None
        flash("validó", "success")
        return redirect(url_for('create_job'))
    elif request.method == "POST":
        print(forms.errors)
        return redirect(url_for('create_job'))

    # print(form.errors)
    # if form.errors:
    #     message = [form.errors.get(key)[0] for key in form.errors]
    #     print(message)
    #     flash(f"{(' - ').join(message)}", "danger")

    return render_template("create-job.html", user=current_user,
                           workers=workers,
                           forms=forms,
                           added_workers=added_workers)


@app.route("/add-worker-to-list", methods=["POST", "GET"])
@login_required
@supplier_only
def add_worker_to_list():
    if request.method == "POST":
        print("+-+-+-", request.form.to_dict())
        if not session.get("workers_to_add"):
            session["workers_to_add"]: list = [(key, int(value)) for key, value in request.form.to_dict().items()]
        else:
            session["workers_to_add"] = session["workers_to_add"] + [(key, int(value)) for key, value in request.form.to_dict().items()]
    print("session", session["workers_to_add"])
    return redirect(url_for('create_job', user=current_user))


@app.route("/remove-worker-from-list", methods=["GET"])
@login_required
@supplier_only
def remove_worker_form_list():
    """remove worker from the list they were added for a job - one at a time"""
    if request.args.get("delete_all"):
        session["workers_to_add"] = None
        return redirect(url_for('create_job', user=current_user))
    not_deleted: list = session.get("workers_to_add")
    not_deleted.pop(int(request.args.get("index")))
    session["workers_to_add"] = not_deleted
    return redirect(url_for('create_job', user=current_user))


@app.route("/del-worker")
@login_required
@supplier_only
def delete_worker():
    worker_id = int(request.args.to_dict().get("worker_id"))
    worker = db.session.query(Worker).filter_by(id=worker_id).first()
    db.session.delete(worker)
    db.session.commit()
    flash("Trabajador elminado correctamente", "success")
    return redirect(url_for('register_worker', user=current_user))



