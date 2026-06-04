# Control Plane Demo Script

Record your screen at 1920×1080. Start with the control plane already open at http://localhost:9700 and Docker running with services started.

---

## Scene 1 — Landing Page (0:00 – 0:30)

**Visual**: Browser at localhost:9700 — dark theme UI fully loaded.

**Narration**:
> "This is the Alfresco Community 26.x Control Plane. It's a web-based dashboard for managing Docker services without using the command line. Zero dependencies — just Python stdlib on the backend and vanilla JavaScript on the frontend."

**Actions**:
- Slow hover over the header showing "alfresco control plane"
- Point to the status badge: "6/6 running"
- Point to Start All / Stop All / Restart All / Refresh buttons

---

## Scene 2 — Services Panel (0:30 – 1:15)

**Visual**: Services table showing alfresco, share, then alphabetical services.

**Narration**:
> "The Services panel lists every service from our docker-compose file. Alfresco and Share always appear first, followed by the rest alphabetically. Each service shows a green or red status dot, and we have Start, Stop, and Restart controls per service or globally."

**Actions**:
- Scroll slowly down the service list
- Hover over a running service row — the row highlights
- Click the **Stop** button on a non-critical service (e.g., `postgres`)
- Wait for the toast: "postgres: stopped"
- Point to the status changing to red
- Click the **Start** button to bring it back up
- Toast: "postgres: started"

---

## Scene 3 — Log Accordion (1:15 – 2:00)

**Visual**: Service row with ▶ Show Logs inline with service name.

**Narration**:
> "Each service has a built-in log viewer. Let's look at what Alfresco is doing."

**Actions**:
- Click **▶ Show Logs** on the `alfresco` row
- Point to the toggle changing to **▼ Hide Logs**
- Point to the log content appearing below in monospace, showing timestamps
- Scroll the log content area
- If services are running: "These are the last 20 lines from Docker logs — timestamps included."
- Click **▶ Show Logs** on `share` to open multiple logs simultaneously
- Collapse both by clicking **▼ Hide Logs**

---

## Scene 4 — Dozzle Integration (2:00 – 2:30)

**Visual**: Dozzle ↗ link next to Show Logs.

**Narration**:
> "We also integrate with Dozzle, a real-time container log viewer that runs alongside Alfresco. Clicking Dozzle takes us directly to that container's logs in the Dozzle UI."

**Actions**:
- Click the **Dozzle ↗** link on the `alfresco` service
- A new tab opens at http://localhost:9999 showing Alfresco logs streaming live
- Switch back to the control plane tab
- "You can monitor all containers in real time without leaving your browser."

---

## Scene 5 — Uploading Files (2:30 – 3:30)

**Visual**: Available Files section at the bottom, Content tab active.

**Narration**:
> "The Available Files section lets us manage files in the installs directories. We can upload AMPs and JARs directly through the browser."

**Actions**:
- Ensure the **Content** tab is active
- Click **Upload File** — the file picker opens
- Select a `.jar` or `.amp` file from a local folder (have one ready)
- Watch the button change to "Uploading..."
- Toast appears: "myfile.jar uploaded"
- Point to the file appearing in the list
- A `confirm()` dialog pops up: "Do you want to install it now?"
- **Click Cancel** to show the dialog, then narrate
- "If we click OK, it would install the file immediately. We'll show that next."

---

## Scene 6 — Installing & Deleting Files (3:30 – 4:30)

**Visual**: File list with Install and Delete buttons.

**Narration**:
> "Each file has an Install button and a Delete button. Let's install a JAR."

**Actions**:
- Click **Install JAR** on a `.jar` file
- Toast: "myfile.jar copied"
- Point to the button showing "(done)" — disabled state
- Switch to the **JARs** tab in the right panel
- "The JAR now appears in WEB-INF/lib — it will be live after the next restart."
- Switch back to the Content tab
- Click **Delete** on the same file
- Confirmation dialog: "WARNING: Deleting files can be dangerous! Are you sure you want to delete..."
- **Click OK**
- Toast: "myfile.jar deleted"
- "The file is removed from the directory. Let's do the same for an AMP."

---

## Scene 7 — AMPs Panel (4:30 – 5:15)

**Visual**: AMPs panel showing installed modules and pending.

**Narration**:
> "The AMPs panel shows us what modules are currently installed inside the container, and what's pending in the amps directory."

**Actions**:
- Point to the **Installed** table — Title, Version, ID columns
- "Here we can see the installed AMPs with their version numbers."
- Point to the **Pending** section below
- "Pending AMPs are files in the container's amps directory waiting to be installed."
- Switch between **Alfresco** and **Share** tabs
- "We can check both containers."

---

## Scene 8 — JARs Panel (5:15 – 5:45)

**Visual**: JARs panel showing all JARs in WEB-INF/lib.

**Narration**:
> "The JARs panel gives us visibility into every JAR deployed in WEB-INF/lib. We can remove individual JARs right from here."

**Actions**:
- Point to the file list with Remove buttons
- Click **Remove** on a non-critical JAR
- Toast: "myfile.jar removed"
- "The JAR is deleted from the running container."

---

## Scene 9 — Refresh & Auto-Refresh (5:45 – 6:00)

**Visual**: Services status and data staying current.

**Narration**:
> "All panels auto-refresh — services every 10 seconds. We can also force an update anytime with the Refresh button."

**Actions**:
- Click the **Refresh** button in the header
- Watch all panels briefly reload
- "Everything stays in sync with the live Docker state."

---

## Scene 10 — Docker Not Running (6:00 – 6:30)

**Visual**: Docker overlay modal (if Docker were stopped).

**Narration**:
> "If Docker isn't running, the UI shows a prompt with a Launch Docker button. It polls every 500 milliseconds and loads the dashboard automatically once Docker is ready."

**Actions** (simulate by stopping Docker or just describe):
- "The overlay has two buttons: Launch Docker and Check Again."
- "No terminal needed — everything is managed from the browser."

---

## Scene 11 — Wrap Up (6:30 – 7:00)

**Visual**: Back to the full dashboard view.

**Narration**:
> "The Alfresco Control Plane puts everything in one place — service management, logs, files, AMPs, and JARs. No dependencies, no installation, no CLI needed. Just Python and a browser."

**Actions**:
- Slow zoom out / wide view of the full page
- Fade to the http://localhost:9700 URL

---

## Recording Tips

- **Resolution**: 1920×1080 at 60fps
- **Cursor**: Use a visible cursor with a highlight ring
- **Audio**: Clear narration, no background music
- **Pacing**: Pause 2–3 seconds after each action before narrating
- **Zoom**: If needed, zoom browser to 110% for readability
- **Preparation**: Have test `.jar` and `.amp` files ready in a folder before recording
- **Outtakes**: Record each scene separately, then stitch together
