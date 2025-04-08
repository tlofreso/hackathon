import os
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta

app = Flask(__name__)
# Secret key for session management (replace with a real secret key in production)
app.secret_key = os.urandom(24)

# --- Policy Details (Hardcoded for Prototype) ---
POLICY_HOLDER = "Main Street Cafe"
POLICY_NUMBER = "BUS-789123"
TRIGGER_HOURS = 4  # Outage duration threshold in hours
PAYOUT_AMOUNT = 500  # Fixed payout amount in $

# --- Simulation State (Using Flask session to store state per user) ---
# In a real app, this state would be managed in a database linked to Ting data
def initialize_state():
    session.setdefault('power_status', 'ON')
    session.setdefault('outage_start_time', None)
    session.setdefault('outage_duration_str', "0h 0m")
    session.setdefault('payout_status', 'Monitoring')
    session.setdefault('last_updated', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/')
def index():
    initialize_state() # Ensure session variables exist

    outage_duration = timedelta(0)
    now = datetime.now()
    session['last_updated'] = now.strftime("%Y-%m-%d %H:%M:%S")

    # Calculate duration if outage is ongoing
    if session.get('power_status') == 'OFF' and session.get('outage_start_time'):
        start_time = datetime.fromisoformat(session['outage_start_time'])
        outage_duration = now - start_time
        total_seconds = int(outage_duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        session['outage_duration_str'] = f"{hours}h {minutes}m"
    else:
         session['outage_duration_str'] = "0h 0m" # Reset if power is on

    # Check payout trigger ONLY if not already triggered/paid
    if session['payout_status'] in ['Monitoring', 'Threshold Met - Pending Payout'] :
        if outage_duration >= timedelta(hours=TRIGGER_HOURS):
            session['payout_status'] = 'Threshold Met - Pending Payout'
        else:
             # Reset if duration dips below threshold (unlikely but handles edge cases)
             # Or keep monitoring if power is still off but threshold not met
             if session['power_status'] == 'OFF':
                 session['payout_status'] = 'Monitoring'

    return render_template('index.html',
                           policy_holder=POLICY_HOLDER,
                           policy_number=POLICY_NUMBER,
                           trigger_hours=TRIGGER_HOURS,
                           payout_amount=PAYOUT_AMOUNT,
                           power_status=session['power_status'],
                           outage_duration_str=session['outage_duration_str'],
                           payout_status=session['payout_status'],
                           last_updated=session['last_updated'])

@app.route('/simulate', methods=['POST'])
def simulate():
    action = request.form.get('action')
    now = datetime.now()

    if action == 'outage_start':
        if session['power_status'] == 'ON': # Only start if power is currently on
            session['power_status'] = 'OFF'
            session['outage_start_time'] = now.isoformat()
            session['payout_status'] = 'Monitoring' # Reset payout status
            session['outage_duration_str'] = "0h 0m"
    elif action == 'power_restored':
        if session['power_status'] == 'OFF': # Only restore if power is currently off
            session['power_status'] = 'ON'
            session['outage_start_time'] = None
            session['outage_duration_str'] = "0h 0m"
            # Keep payout status if it was triggered, otherwise reset to Monitoring
            if session['payout_status'] not in ['Threshold Met - Pending Payout', 'Payout Initiated', 'Payout Processed']:
                 session['payout_status'] = 'Monitoring'
    elif action == 'force_trigger':
        # Simulate time passing instantly to meet the trigger
        if session['power_status'] == 'OFF' and session['outage_start_time']:
            # Force start time to be longer ago than threshold
            session['outage_start_time'] = (now - timedelta(hours=TRIGGER_HOURS, minutes=1)).isoformat()
        elif session['power_status'] == 'ON': # If power is on, simulate an outage that already met threshold
             session['power_status'] = 'OFF'
             session['outage_start_time'] = (now - timedelta(hours=TRIGGER_HOURS, minutes=1)).isoformat()
        session['payout_status'] = 'Threshold Met - Pending Payout' # Ensure status reflects trigger
    elif action == 'initiate_payout':
        if session['payout_status'] == 'Threshold Met - Pending Payout':
            session['payout_status'] = 'Payout Initiated'
            # In real app: Call payment API here
    elif action == 'mark_paid':
        if session['payout_status'] == 'Payout Initiated':
            session['payout_status'] = 'Payout Processed'
    elif action == 'reset':
        session.clear() # Clear the session state completely
        initialize_state() # Re-initialize default state


    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) # Debug mode is helpful during development