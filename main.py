from flask import Flask, render_template, request, session, redirect
from flask_session import Session
import sqlite3, time

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config.update(SECRET_KEY='b^\x80\xc6P\x11zY\xda\xd9\x02~/@w\xabJ')

# VARIABLES HERE
dbName = "logins.db"

@app.route("/")
def hello_world():
    if(session.get("user_logged")):
        return redirect("/events")
    else:
        return render_template("index.html")

@app.route("/login",methods = ['POST', 'GET'])
def loginPage():
    session.clear()
    if(request.method == "GET"):
        return render_template("login.html")
    elif(request.method == "POST"):
        
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(dbName)
        cur = conn.cursor()
        cur.execute(f"SELECT USERNAME,PERMISSIONLEVEL FROM LOGINS WHERE USERNAME='{username}' AND PASSWORD = '{password}';")
        returnVal = cur.fetchone()
        if not returnVal:
            return "Login Failure"
        else:
            session["permissionLevel"] = returnVal[1]
            session["user_logged"] = username
            return redirect("/")

@app.route("/createAccount", methods=["POST","GET"])
def createAccount():
    if(request.method == "GET"):
        return render_template("createAccount.html")
    elif(request.method == "POST"):
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(dbName)
        # PASSWORD IS IN PLAINTEXT FOR NOW, NAUGHTY NAUGHTY (YOU GET NO BITCHES, TRENT)
        conn.execute("INSERT INTO LOGINS (USERNAME, PASSWORD) VALUES (?,?);", (username, password))
        conn.commit()
        conn.close()
        
        return redirect("/events")

@app.route("/logout")
def logoutAccount():
    #Handles logging the user out by changing the user logged to a null value basically
    if(not session.get("user_logged")):
        return redirect("/login")
    session["user_logged"] = None
    return redirect("/")

@app.route("/events")
def events():
    #Shows a list of events.
    if(not session.get("user_logged")):
        return redirect("/login")
    
    conn = sqlite3.connect(dbName)
    cur = conn.cursor()
    cur.execute("SELECT ID,NAME,DATE FROM EVENTS")
    eventsResp = cur.fetchall()
    conn.close()

    eventList = []
    for event in eventsResp:
        eventList.append({
            "id":event[0],
            "name":event[1],
            "date":str(event[2])
        })

    

    return render_template("events.html",username=session.get("user_logged"),permissionLevel=session.get("permissionLevel"),events=eventList)

@app.route("/event/")
def event():
    #displays the event page
    if(not session.get("user_logged")):
        return redirect("/login")
    eventId = request.args.get("id")
    if eventId:
        # Insert code to fetch event information here
        conn = sqlite3.connect(dbName)
        cur = conn.cursor()
        cur.execute("SELECT ID, NAME, DATE, LOCATION, MANDATORY FROM EVENTS WHERE ID = (?)",(eventId,))

        eventsResp = cur.fetchone()
        eventData = {
            "id":eventsResp[0],
            "name":eventsResp[1],
            "date":eventsResp[2],
            "mandatory":eventsResp[4],
            "location":eventsResp[3]
        }
        if eventData['mandatory'] == 1:
            eventData['mandatory'] = "This is a mandatory event."
        elif eventData['mandatory'] == 0:
            eventData['mandatory'] = "This is not mandatory."
        
        excuses = []
        notattendings = []
        attendings = []
        if session.get("permissionLevel") > 0:
            cur.execute("SELECT ID, USERNAME, EXCUSETXT, STATUS FROM EXCUSES WHERE EVENTID = (?)",(eventId,))
            excusesResp = cur.fetchall()
            cur.execute("SELECT NOTATTENDING FROM EVENTS WHERE ID = (?)", (eventId))
            notattendingsResp = cur.fetchone()
            #cur.execute("SELECT ATTENDEES FROM EVENTS WHERE ID = (?)", (eventId))
            #attendingsResp = cur.fetchall()
            
            for excuse in excusesResp:
                print(excuse)
                excuses.append({
                    "eventId":eventId,
                    "id":excuse[0],
                    "username":excuse[1],
                    "excuseText":excuse[2],
                    "approved":excuse[3],
                })
            
            if(notattendingsResp[0]):
                notattendings = str(notattendingsResp[0]).split(",")
            else:
                notattendings = []
    
            attendings = getAttendees(eventId)

            print(attendings)
        conn.close()
        print(isAttending(username=session.get("user_logged"),eventID=eventId))
        return render_template("event.html",username=session.get("user_logged"),
        permissionLevel=session.get("permissionLevel"),
        event=eventData,
        excuses=excuses,
        isAttending=isAttending(username=session.get("user_logged"),eventID=eventId),
        excuseStatus=getExcuseStatus(session.get("user_logged"),eventId),
        notattendings=notattendings,
        attendings=attendings
        )
    else:
        return redirect("/events")

@app.route("/attending")
def attend():
    #Adds the user to the list of attendees for a specified event
    if(not session.get("user_logged")):
        return redirect("/login")
    eventId = request.args.get("id")
    username = session.get("user_logged")
    
    if isAttending(username=username,eventID=eventId):
        return redirect('/event?id=' + eventId)
    conn = sqlite3.connect(dbName)
    cur = conn.cursor()
    cur.execute("SELECT ATTENDEES FROM EVENTS WHERE ID = (?)",(eventId,))

    attendees = cur.fetchone()[0]

    if attendees == None:
        attendees = str(username)
    else:
        attendees = str(username) + "," + str(attendees)

    cur.execute("UPDATE EVENTS SET ATTENDEES = (?) WHERE ID = (?)", (attendees, eventId))
    conn.commit()
    conn.close()
    
    print(attendees)
    return redirect('/event?id=' + eventId)

@app.route('/notattending')
def not_attend():
    #Adds the user to the list of attendees for a specified event
    if(not session.get("user_logged")):
        return redirect("/login")
    eventId = request.args.get("id")
    username = session.get("user_logged")
    
    if isAttending(username=username,eventID=eventId):
        return redirect('/event?id=' + eventId)
    conn = sqlite3.connect(dbName)
    cur = conn.cursor()
    cur.execute("SELECT NOTATTENDING FROM EVENTS WHERE ID = (?)",(eventId,))

    attendees = cur.fetchone()[0]

    if attendees == None:
        attendees = str(username)
    else:
        attendees = str(username) + "," + str(attendees)

    cur.execute("UPDATE EVENTS SET NOTATTENDING = (?) WHERE ID = (?)", (attendees, eventId))
    conn.commit()
    conn.close()
    
    print(attendees)
    return redirect('/event?id=' + eventId)

@app.route('/submitExcuse', methods=['POST'])
def submit_excuse():
    eventId = request.form["eventId"]
    excuseTxt = request.form["excuseTxt"]
    username = request.form["username"]

    conn = sqlite3.connect(dbName)
    cur = conn.cursor()
    # PASSWORD IS IN PLAINTEXT FOR NOW, NAUGHTY NAUGHTY (YOU GET NO BITCHES, TRENT)
    cur.execute("INSERT INTO EXCUSES (USERNAME, EVENTID, EXCUSETXT) VALUES (?,?,?);", (username, eventId, excuseTxt))
    conn.commit()
    conn.close()

    return redirect('/event?id=' + eventId)

@app.route('/approveExcuse')
def excuse_approve():
    #Approves the excuse and moves the user to "Not attending"
    if(not session.get("user_logged")):
        return redirect("/login")
    excuseID = request.args.get("id")
    eventID = str(setExcuseStatus(excuseID, 1))

    conn = sqlite3.connect(dbName)
    cur = conn.cursor()
    # PASSWORD IS IN PLAINTEXT FOR NOW, NAUGHTY NAUGHTY (YOU GET NO BITCHES, TRENT)
    cur.execute("SELECT USERNAME FROM EXCUSES WHERE ID = (?)", (excuseID,))
    username = cur.fetchone()[0]
    print(username)
    cur.execute("SELECT NOTATTENDING FROM EVENTS WHERE ID =  (?)", (eventID,))
    notAttendings = cur.fetchone()[0]
    if notAttendings == None:
        notAttendings = str(username)
    else:
        notAttendings = str(username) +","+ str(notAttendings)
    cur.execute("UPDATE EVENTS SET NOTATTENDING = (?) WHERE ID = (?)", (notAttendings,eventID))
    conn.commit()
    conn.close()

    return redirect('/event?id=' + eventID)

@app.route('/denyExcuse')
def excuse_deny():
    #denys the excuse.
    if(not session.get("user_logged")):
        return redirect("/login")
    excuseID = request.args.get("id")
    
    eventID = str(setExcuseStatus(excuseID, 0))
    return redirect('/event?id=' + eventID)


@app.route("/createEvent", methods=["POST","GET"])
def createEvent():
    #Creates a new event
    if(not session.get("user_logged") or session.get("permissionLevel") == 0):
        return redirect("/login")
    if(request.method == "GET"):
        return render_template("createEvent.html",username=session.get("user_logged"))
    elif(request.method == "POST"):
        name = request.form['name']
        date = request.form['date']
        location = request.form['location']
        mandatory = request.form.get("mandatory")
        if mandatory == None:
            mandatory = 0 
            
        conn = sqlite3.connect(dbName)
        cur = conn.cursor()
         # PASSWORD IS IN PLAINTEXT FOR NOW, NAUGHTY NAUGHTY (YOU GET NO BITCHES, TRENT)
        conn.execute("INSERT INTO Events (NAME, DATE, LOCATION, MANDATORY) VALUES (?,?,?,?);", (name, date, location, mandatory))
        conn.commit()
        cur.execute("SELECT ID FROM EVENTS WHERE NAME = (?);", (name,))
        id = str(cur.fetchone()[0])
        conn.close()
        
        return redirect("/event?id="+id)

@app.route("/checkin")
def checkIn():
    if(not session.get("user_logged") or session.get("permissionLevel") == 0):
        return redirect("/login")
    username = request.args.get("username")
    eventId = request.args.get("eventId")
    conn = sqlite3.connect(dbName)
    cur = conn.cursor()
    # PASSWORD IS IN PLAINTEXT FOR NOW, NAUGHTY NAUGHTY (YOU GET NO BITCHES, TRENT)
    cur.execute("SELECT CHECKEDIN FROM EVENTS WHERE ID= (?)",(eventId,))
    checkedin = cur.fetchone()[0]
    if checkedin == None:
        checkedin = str(username)
    else:
        checkedin = str(username) + "," + str(checkedin)
    cur.execute("UPDATE EVENTS SET CHECKEDIN = (?) WHERE ID = (?)", (checkedin,eventId))
    conn.commit()
    conn.close()
    return redirect("/event?id="+eventId)

@app.route("/profile")
def profile():
    if(not session.get("user_logged")):
        return redirect("/login")
    username = request.args.get("username")
    conn = sqlite3.connect(dbName)
    cur = conn.cursor()
    cur.execute("SELECT USERNAME,PERMISSIONLEVEL,EMAIL,FIRSTNAME,LASTNAME,PHONE FROM LOGINS WHERE USERNAME = (?)",(username,))
    result = cur.fetchone()
    userData = {
        "username":result[0],
        "permissionlevel":result[1],
        "email":result[2],
        "firstname":result[3],
        "lastname":result[4],
        "phone":result[5]
    }
    conn.commit()
    conn.close()
    return render_template("profile.html",username = session.get("user_logged"), data=userData)

@app.route("/directory")
def directory():
    if(not session.get("user_logged")):
        return redirect("/login")
    userData = []
    conn = sqlite3.connect(dbName)
    cur = conn.cursor()
    cur.execute("SELECT USERNAME,EMAIL,FIRSTNAME,LASTNAME FROM LOGINS")
    results = cur.fetchall()
    for result in results:
        userData.append({
            "username":result[0],
            "email":result[1],
            "firstname":result[2],
            "lastname":result[3],
        })
    conn.commit()
    conn.close()
    return render_template("directory.html", username=session.get("user_logged"),data=userData)

@app.errorhandler(404)
def page_not_found(e):
    if(not session.get("user_logged")):
        return redirect("/login")
    return render_template('404.html',username=session.get("user_logged")), 404


#Checks to see if a user is attending a certain event
def isAttending(username,eventID):
        conn = sqlite3.connect(dbName)
        cur = conn.cursor()
         # PASSWORD IS IN PLAINTEXT FOR NOW, NAUGHTY NAUGHTY (YOU GET NO BITCHES, TRENT)
        cur.execute("SELECT ATTENDEES,NOTATTENDING FROM EVENTS WHERE ID = (?)", (eventID,))
        resp = cur.fetchone()
        if resp != None:
            attendees = str(resp[0]).split(",")
            notAttending = str(resp[1]).split(",")
            
            if username in attendees:
                conn.close()
                return True
            if username in notAttending:
                conn.close()
                return False
            return None
        else:
            conn.close()
            return None
        
def getAttendees(eventID):
        attendees = []
        conn = sqlite3.connect(dbName)
        cur = conn.cursor()
         # PASSWORD IS IN PLAINTEXT FOR NOW, NAUGHTY NAUGHTY (YOU GET NO BITCHES, TRENT)
        cur.execute("SELECT ATTENDEES, CHECKEDIN FROM EVENTS WHERE ID = (?)", (eventID,))
        resp = cur.fetchone()
        if resp[0] != None:
            conn.close()
            attendeelist = str(resp[0]).split(",")
            checkedInList = str(resp[1]).split(",")
            for attendee in attendeelist:
                checkedIn = (attendee in checkedInList)
                attendees.append({
                    "username": attendee,
                    "checkedIn":checkedIn
                })
            return attendees
        else:
            conn.close()
            return []

def getExcuseStatus(username, eventID):
    conn = sqlite3.connect(dbName)
    cur = conn.cursor()
    # PASSWORD IS IN PLAINTEXT FOR NOW, NAUGHTY NAUGHTY (YOU GET NO BITCHES, TRENT)
    cur.execute("SELECT STATUS FROM EXCUSES WHERE EVENTID = (?) AND USERNAME = (?)", (eventID,username))
    resp = cur.fetchone()
    if resp != None:
        conn.close()
        return resp[0]
    else:
        conn.close()
        return None

def setExcuseStatus(excuseID,status):
    conn = sqlite3.connect(dbName)
    cur = conn.cursor()
    # PASSWORD IS IN PLAINTEXT FOR NOW, NAUGHTY NAUGHTY (YOU GET NO BITCHES, TRENT)
    cur.execute("UPDATE EXCUSES SET STATUS = (?) WHERE ID = (?)", (status,excuseID))
    conn.commit()
    cur.execute("SELECT EVENTID FROM EXCUSES WHERE ID=?",(excuseID,))
    resp = cur.fetchone()
    eventID = resp[0]
    conn.close()
    return eventID

if __name__ == '__main__':
    # run() method of Flask class runs the application 
    # on the local development server.
    app.run(debug=True)


# ———————————No bitches?———————————
# ⠀⣞⢽⢪⢣⢣⢣⢫⡺⡵⣝⡮⣗⢷⢽⢽⢽⣮⡷⡽⣜⣜⢮⢺⣜⢷⢽⢝⡽⣝
# ⠸⡸⠜⠕⠕⠁⢁⢇⢏⢽⢺⣪⡳⡝⣎⣏⢯⢞⡿⣟⣷⣳⢯⡷⣽⢽⢯⣳⣫⠇
# ⠀⠀⢀⢀⢄⢬⢪⡪⡎⣆⡈⠚⠜⠕⠇⠗⠝⢕⢯⢫⣞⣯⣿⣻⡽⣏⢗⣗⠏⠀
# ⠀⠪⡪⡪⣪⢪⢺⢸⢢⢓⢆⢤⢀⠀⠀⠀⠀⠈⢊⢞⡾⣿⡯⣏⢮⠷⠁⠀⠀
# ⠀⠀⠀⠈⠊⠆⡃⠕⢕⢇⢇⢇⢇⢇⢏⢎⢎⢆⢄⠀⢑⣽⣿⢝⠲⠉⠀⠀⠀⠀
# ⠀⠀⠀⠀⠀⡿⠂⠠⠀⡇⢇⠕⢈⣀⠀⠁⠡⠣⡣⡫⣂⣿⠯⢪⠰⠂⠀⠀⠀⠀
# ⠀⠀⠀⠀⡦⡙⡂⢀⢤⢣⠣⡈⣾⡃⠠⠄⠀⡄⢱⣌⣶⢏⢊⠂⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⢝⡲⣜⡮⡏⢎⢌⢂⠙⠢⠐⢀⢘⢵⣽⣿⡿⠁⠁⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠨⣺⡺⡕⡕⡱⡑⡆⡕⡅⡕⡜⡼⢽⡻⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⣼⣳⣫⣾⣵⣗⡵⡱⡡⢣⢑⢕⢜⢕⡝⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⣴⣿⣾⣿⣿⣿⡿⡽⡑⢌⠪⡢⡣⣣⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⡟⡾⣿⢿⢿⢵⣽⣾⣼⣘⢸⢸⣞⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# ⠀⠀⠀⠀⠁⠇⠡⠩⡫⢿⣝⡻⡮⣒⢽⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
# —————————————————————————————