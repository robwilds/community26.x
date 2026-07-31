# Control Plane Demo Script

Record your screen at 1920×1080. Start with the control plane already open at http://localhost:9700 and Docker running with services started.

---

## Scene 1 — Landing Page (0:00 – 0:40)

**Visual**: Browser at localhost:9700 — dark theme UI fully loaded.

**Narration**:
> "This is the Alfresco Community 26.x Control Plane. It's a web-based dashboard for managing Docker services without using the command line. Zero dependencies — just Python stdlib on the backend and vanilla JavaScript on the frontend."

**Actions**:
- Slow hover over the header showing "alfresco control plane"
- Point to the status badge: "X/Y running" — green when all running, red otherwise
- Point to Start All / Stop All / Restart All buttons — note they auto-disable: Start All disabled when all running, Stop All / Restart All disabled when none running
- Point to the **?** button (restarts the guided tour on click)
- Point to the **Open Alfresco ↗** link — appears whenever any service is running
- Point to the **Refresh** button

---

## Scene 2 — Services Panel (0:40 – 1:30)

**Visual**: Services table showing alfresco, share, then alphabetical services.

**Narration**:
> "The Services panel lists every service from our docker-compose file. Alfresco and Share always appear first, followed by the rest alphabetically. Services with a `profiles: [donotstart]` config get a badge and are excluded from the default start. Each service shows a green or red status dot, and we have Start, Stop, and Restart controls per service or globally."

**Actions**:
- Scroll slowly down the service list
- Hover over a profile-tagged service — point out the "profile: donotstart" badge
- Hover over a running service row — the row highlights
- Click the **Stop** button on a non-critical service (e.g., `postgres`)
- Wait for the toast: "postgres: stopped"
- Point to the status changing to red, global Stop All button disabling
- Click the **Start** button to bring it back up
- Toast: "postgres: started"

---

## Scene 3 — Log Accordion & Dozzle (1:30 – 2:30)

**Visual**: Service row with ▶ Show Logs and Dozzle ↗ inline with service name.

**Narration**:
> "Each service has a built-in log viewer and integrates with Dozzle for real-time monitoring."

**Actions**:
- Click **▶ Show Logs** on the `alfresco` row
- Point to the toggle changing to **▼ Hide Logs**
- Point to the log content appearing below in monospace, showing timestamps
- Scroll the log content area
- Click **▶ Show Logs** on `share` to open multiple logs simultaneously
- Collapse both by clicking **▼ Hide Logs**
- Click the **Dozzle ↗** link on the `alfresco` service
- A new tab opens at http://localhost:9999 showing Alfresco logs streaming live
- Switch back to the control plane tab
- "You can monitor all containers in real time without leaving your browser."

---

## Scene 4 — Guided Tour (2:30 – 3:15)

**Visual**: The guided tour overlay appears, dimming the background and highlighting elements.

**Narration**:
> "On first visit, a built-in guided tour walks through every area of the UI. It highlights each panel in sequence with a description — no learning curve."

**Actions**:
- On a fresh browser (or click the **?** button to restart), the tour starts after 2 seconds
- Step 1 highlights the **Service Controls** — Start All / Stop All / Restart All with tooltip
- Click **OK** to advance
- Step 2 highlights the **Services Table** — per-service status and controls
- Step 3 highlights **Logs & Monitoring** — Show Logs and Dozzle ↗
- Step 4 highlights **File Management** — Upload, Install, Delete
- Step 5 highlights the **AMPs** panel — installed modules and pending
- Step 6 highlights the **JARs** panel — WEB-INF/lib listing with Remove
- After step 6, the tour ends automatically
- "The tour runs once per browser tracked via localStorage. Click **?** anytime to restart it."

---

## Scene 5 — Uploading Files (3:15 – 4:15)

**Visual**: Available Files section, Content tab active.

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

## Scene 6 — Installing & Deleting Files (4:15 – 5:00)

**Visual**: File list with Install AMP / Install JAR and Delete buttons.

**Narration**:
> "Each file has an Install button and a Delete button. Install buttons are disabled when Docker isn't running, with a message indicating they will be enabled once Docker starts. Let's install a JAR."

**Actions**:
- Click **Install JAR** on a `.jar` file
- Toast: "myfile.jar copied"
- Point to the button showing "(done)" — disabled state indicating already installed
- Switch to the **JARs** tab in the right panel
- "The JAR now appears in WEB-INF/lib — it will be live after the next restart."
- Switch back to the Content tab
- Click **Delete** on the same file
- Confirmation dialog: "WARNING: Deleting files can be dangerous! Are you sure you want to delete..."
- **Click OK**
- Toast: "myfile.jar deleted"
- "The file is removed from the directory."

---

## Scene 7 — AMPs Panel (5:00 – 5:40)

**Visual**: AMPs panel showing installed modules, available from installs/, and pending.

**Narration**:
> "The AMPs panel shows installed modules, available AMPs from the local installs directory, and what's pending in the container's amps dir ready to be installed."

**Actions**:
- Point to the **Installed** table — Title, Version, ID columns, each with a **Remove** button
- "Every installed AMP can be removed, even those baked into the image."
- Click **Remove** on an installed AMP
- Toast: "removed and available for reinstall"
- "The AMP is uninstalled and reappears in Available, ready to be reinstalled with one click."
- Point to the **Available (in installs/)** section below — lists AMPs in the local installs/ directory with **Install** buttons
- "Available AMPs can be installed directly from the browser."
- Point to the **Pending** section — lists AMP files in the container's amps dir (filtered to exclude already-installed AMPs)
- Switch between **Alfresco**, **Share**, and **All Services** tabs
- "The All Services tab aggregates both containers."

---

## Scene 8 — JARs Panel (5:40 – 6:10)

**Visual**: JARs panel showing installed JARs, available from installs/, and all three tabs.

**Narration**:
> "The JARs panel gives us visibility into every JAR deployed in WEB-INF/lib and available in the local installs directory. We can install, remove, and track JARs across both containers."

**Actions**:
- Point to the **Installed** list with Remove buttons
- Point to the **Available (in installs/)** section with Install buttons
- Switch between **Alfresco**, **Share**, and **All Services** tabs
- "The All Services tab shows both containers with service badges, just like AMPs does."
- Click **Remove** on a non-critical JAR
- Toast: "myfile.jar removed"
- "The JAR is deleted from the running container. Available JARs can be deployed with one click."

---

## Scene 9 — Refresh & Auto-Refresh (6:10 – 6:30)

**Visual**: Services status and data staying current.

**Narration**:
> "All panels auto-refresh — services every 10 seconds. We can also force an update anytime with the Refresh button."

**Actions**:
- Click the **Refresh** button in the header
- Watch all panels briefly reload
- "Everything stays in sync with the live Docker state."

---

## Scene 10 — Alfresco Ready Prompt (6:30 – 7:00)

**Visual**: Alfresco goes from stopped to running; a modal overlay appears.

**Narration**:
> "When Alfresco starts up and its health probe returns healthy, a popup prompts you to open the application directly."

**Actions**:
- Start the Alfresco service if stopped
- Wait for the "Alfresco is ready" overlay to appear
- Point to the **Open Alfresco** button and **Not now** dismiss button
- "Click Open Alfresco to launch http://localhost:8080/alfresco in a new tab, or dismiss it."
- Click **Not now** to close the prompt
- "The prompt only appears once per session."

---

## Scene 11 — Docker Not Running (7:00 – 7:30)

**Visual**: Docker overlay modal.

**Narration**:
> "If Docker isn't installed, the UI shows a 'Download Docker Desktop' link. If it's installed but not running, it shows a Launch Docker button. It polls every 500 milliseconds and loads the dashboard automatically once Docker is ready."

**Actions** (simulate by stopping Docker or just describe):
- "The overlay adapts: Docker not installed → Download link; Docker not running → Launch Docker + Check Again buttons."
- "Once launched, a waiting screen appears and polls until Docker responds."
- "No terminal needed — everything is managed from the browser."

---

## Scene 12 — Wrap Up (7:30 – 8:00)

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
- **Tour**: Clear `localStorage` or use the **?** button to restart the guided tour on demand
