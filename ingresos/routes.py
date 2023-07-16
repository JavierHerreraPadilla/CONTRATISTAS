import os
from io import BytesIO
from pathlib import Path
from ingresos import app, db
from flask import session, render_template, request, redirect, url_for, flash, send_from_directory
from .models import Client, Supplier, Worker, Job, JobWorker, ClientVenue, SupplierAssignedJobs, WorkerRequirements
from .forms import LoginForm, RegisterForm, WorkerForm, JobForm, AssignedJobForm, MultipleJobForm, WorkerRequirementsForm
from flask_login import login_user, logout_user, login_required, current_user, LoginManager
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
    return render_template("supp_panel.html", user=current_user,
                           current_date=datetime.now())


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
        flash("Sede creada. Puedes editar el nombre.", "info")
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


import requests
url_departamentos = "https://municipiosapi-1-p3448576.deta.app/all"

@app.route("/register-worker", methods=["POST", "GET"])
@login_required
@supplier_only
def register_worker():
    """this route allows suppliers to create their workers"""
    req_form = WorkerRequirementsForm(req_date=datetime.now().date())
    session["workers_to_add"] = None  # esto es para borrar la lista de trabajadores añadadidos al momento de registrar una tarea
    form = WorkerForm()
    # form.residency_state.choices = requests.get(url_departamentos).json() #this works but i need to be connected to the internet for it to use my API
    form.residency_state.choices = ["Antioquia", "Bolívar"]
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
        flash(f"Trabajador {new_worker.first_name} {new_worker.last_name} creado correctamento", "success")
        return redirect(url_for('register_worker'))

    return render_template("register-worker.html", user=current_user, form=form,
                               workers=workers,
                               req_form=req_form,
                               current_date=datetime.now().date()
                               )


@app.route("/edit-worker-info", methods=["POST"])
@login_required
@supplier_only
def edit_worker_info():
    """edita la información de un trabajador ya creado"""
    form = WorkerForm()
    if form.validate_on_submit():
        worker_to_edit = db.session.query(Worker).filter_by(id=int(request.form["worker_id"])).first()
        for key in form.data:
            if key in ["csrf_token", "submit"]:
                continue
            setattr(worker_to_edit, key, form.data[key])
            db.session.commit()
        flash("Información editada", "success")
        return redirect(url_for('register_worker'))
    else:
        return f"{form.errors}"


@app.route("/create-job", methods=["POST", "GET"])
@login_required
@supplier_only
def create_job():
    added_workers = list(enumerate([db.session.query(Worker).filter_by(id=worker_id[1]).first() for worker_id in session.get("workers_to_add")])) if session.get("workers_to_add") else None
    forms = MultipleJobForm(jobs=[{}] * len(added_workers)) if added_workers else None
    if added_workers:
        for form in forms._fields.get("jobs"):
            form.assigned_jobs.choices = [(job.id, job.description) for job in current_user.assigned_jobs]
            form.venue.choices = [(venue.id, venue.venue_name) for venue in current_user.client.venues] #list(enumerate(current_user.client.venues))
    workers = [worker for worker in current_user.workers if worker.is_active]
    if request.method == "POST" and forms.validate_on_submit():
        print("validaron todas", forms.data)
        worker_objs = [worker_obj[1] for worker_obj in added_workers]
        temp_jobs = list()
        for job in zip(worker_objs, forms.data.get('jobs')):
            new_job = Job(title=db.session.query(SupplierAssignedJobs).filter_by(id=job[1].get("assigned_jobs")).first().description,
                          description=job[1].get("assigned_jobs"),
                          start_date=job[1].get("start_date"),
                          end_date=job[1].get("end_date"),
                          supplier_id=current_user.id,
                          client_venue_id=job[1].get("venue"),
                          )
            temp_jobs.append(new_job)
            db.session.add(new_job)
            db.session.flush()
            new_job_worker = JobWorker(job_id=new_job.id,
                                        worker_id=job[0].id
                            )
            db.session.add(new_job_worker)
            db.session.commit()
            flash("Trabajos registrados", "success")
        return redirect(url_for('create_job'))
    elif request.method == "POST":
        flash(f"{forms.errors}", "warning")
        return redirect(url_for('create_job', current_date=datetime.now()))
    return render_template("create-job.html", user=current_user,
                           workers=workers,
                           forms=forms,
                           added_workers=added_workers,
                           current_date=datetime.now())


@app.route("/add-worker-to-list", methods=["POST", "GET"])
@login_required
@supplier_only
def add_worker_to_list():
    if request.method == "POST":
        if not session.get("workers_to_add"):
            session["workers_to_add"]: list = [(key, int(value)) for key, value in request.form.to_dict().items()]
        else:
            session["workers_to_add"] = session["workers_to_add"] + [(key, int(value)) for key, value in request.form.to_dict().items()]
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


@app.route("/del-worker", methods=["POST"])
@login_required
@supplier_only
def delete_worker():
    if request.form["password"] == current_user.password:
        worker_id = int(request.args.to_dict().get("worker_id"))
        worker = db.session.query(Worker).filter_by(id=worker_id).first()
        db.session.delete(worker)
        db.session.commit()
        message = "Trabajador elminado correctamente" if not worker.is_active else "Se reactivó el trabajador"
        flash(message, "success")
        return redirect(url_for('register_worker', user=current_user))
    flash("Contraseña incorrecta", "danger")
    return redirect(url_for('register_worker'))


@app.route("/sup-reports")
@login_required
@supplier_only
def supp_reports():
    """Shows info on the jobs done by the logged supplier"""
    today = datetime.now().date()
    return render_template('supp-reports.html', user=current_user, today=today)


@app.route("/delete-job/<int:job_id>")
@login_required
@supplier_only
def delete_job(job_id):
    job_to_delete = db.session.query(Job).get(job_id)
    db.session.delete(job_to_delete)
    db.session.commit()
    flash("Trabajo eliminado", "info")
    return redirect(url_for("supp_reports"))
@app.route("/add_worker_requirements", methods=["POST"])
@login_required
@supplier_only
def add_worker_requirements():
    """para añadair los requerimientos mensuales del trabajador
    ej: parafiscales, cursos, ..."""
    req_form = WorkerRequirementsForm()
    if req_form.validate_on_submit():
        file = req_form.req_doc.data
        worker = db.session.query(Worker).filter_by(id=req_form.worker_id.data).first()
        worker_identification = worker.identification
        worker_name = worker.first_name + worker.last_name
        print(request.files)
        file_name = f"PLANILLA - {worker_identification} - {req_form.req_date.data}" + ".pdf"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file_name)
        if file_name in os.listdir(app.config['UPLOAD_FOLDER']):
            flash(f"Planilla para el trabajador { worker_name.upper()} "
                  f"en el mes de {req_form.req_date.data.strftime('%B')} ya existe.", "info")
            return redirect(url_for("register_worker", user=current_user))
        new_req = WorkerRequirements(para_date=req_form.req_date.data,
                                     document=file_name,
                                     radication_number=req_form.radication_number.data,
                                     until_date=req_form.req_date.data + timedelta(days=30),
                                     worker_id=req_form.worker_id.data,
                                         )
        file.save(file_path)
        db.session.add(new_req)
        db.session.commit()

        flash("Parafiscales registrados", "success")
    else:
        flash(f"{req_form.errors}", "warning")
    return redirect(url_for('register_worker', user=current_user))


@app.route("/serve_document/<int:requirement_id>")
@login_required
def serve_document(requirement_id):
    """Descarga el pdf plailla parafiscales"""
    # todo cambiar el url_parameter de requirement_id a nombre del documento. Es más seguro
    file_name = db.session.query(WorkerRequirements).filter_by(id=int(requirement_id)).first().document
    file_path = app.config["UPLOAD_FOLDER"] / Path(file_name)
    if file_path.exists():
        return send_from_directory(file_path.parent.absolute(), file_path.name)
    else:
        flash("El documento no existe", "info")
        return redirect(url_for('register_worker', user=current_user))


@app.route("/diable-worker/<int:worker_id>", methods=["POST", "GET"])
def disable_worker(worker_id):
    """this route disables an active worker.
    If an active worker is disabled, it won't be possible to activate them again
    this is goign to take """
    if request.form.get("password") != current_user.password:
        flash("Contraseña incorrecta. No se desactivó trabajador", "danger")
        return redirect(url_for("register_worker"), user=current_user)
    worker_to_disable = db.session.query(Worker).get(worker_id)
    worker_to_disable.is_active = not worker_to_disable.is_active
    db.session.commit()
    flash(f"trabajdor desactivado {worker_id} - {worker_to_disable}", "info")
    return redirect(url_for("register_worker", user=current_user))


import sys

@login_required
@supplier_only
@app.route("/planilla_masiva/", methods=["POST", "GET"])
def planilla_masiva():
    form = WorkerRequirementsForm()
    workers = [worker for worker in current_user.workers if worker.is_active]

    if form.validate_on_submit():
        # todo agregar todos los paraficales a cada trabajdor
        file = form.req_doc.data
        file_content = file.read()
        for index, worker in enumerate(workers):
            worker_identification = worker.identification
            file_name = f"PLANILLA - {worker_identification} - {form.req_date.data}" + ".pdf"
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file_name)
            print("before", file.read())
            # file.save(file_path)
            with open(file_path, "wb") as f:
                f.write(file_content)

            new_requeirement = WorkerRequirements(
                para_date=form.req_date.data,
                radication_number=form.radication_number.data,
                until_date=form.req_date.data + timedelta(days=30),
                worker_id=worker.id,
                document=file_name
            )
            db.session.add(new_requeirement)
            db.session.commit()
            flash("Requerimientos registrados", "info")
    elif request.method == "POST":
        flash(f"{form.errors}", "danger")

    return render_template("planilla_masiva.html", user=current_user,
                           workers=workers,
                           current_date=datetime.now().date(),
                           form=form)







