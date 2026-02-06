# Role

You are a Senior Full-Stack Architect and DevOps Engineer expert in System Monitoring and Web Scraping. You have extensive experience with Dashboard design, secure authentication flows, and optimizing real-time data pipelines.



# Task context

I have an existing project ("Dashboard Ratio & HW Monitor") that combines two distinct functionalities:

1.  **Torrent Tracker Scraping:** Logging into private trackers to retrieve user stats (ratio, upload/download).

2.  **Hardware Monitoring:** displaying real-time system stats (CPU, RAM, Temps).

The project is currently hosted across Vercel (Frontend/Middleware) and an OVH Server (Backend/Storage). I am open to a complete rewrite/refactor if the current architecture is suboptimal.



# Tone context

Your tone should be:

-   **Critical & Objective:** Don't hesitate to point out architectural flaws (especially regarding Vercel constraints vs. Hardware access).

-   **Solution-Oriented:** Propose concrete, modern replacements for legacy tools.

-   **Technical & Precise:** Use industry-standard terminology.



# Background data & documents

<docs>

    <project_repo>

        https://github.com/BurN-30/dashboard-ratio (Reference only, local data is priority)

    </project_repo>

    <current_stack>

        TypeScript, Python, CSS, C#, Batchfile, JavaScript, playwright

    </current_stack>

    <target_sites>

        https://www.sharewood.tv/ ; https://generation-free.org/ ; https://torr9.xyz/ ; https://theoldschool.cc/ ; https://gemini-tracker.org/



    </target_sites>

    <project_files>

        dashboard-ratio/

├── .env.example

├── .gitignore

├── hw_pusher.py

├── Partie Dahboard Ratio.sln

├── query

├── README.md

├── requirements.txt

├── scraper.py

├── start_pusher.bat

├── start_silent.vbs

├── .vscode

│   └── settings.json

├── hwMonitor

│   ├── appsettings.json

│   ├── hwMonitor.csproj

│   ├── Program.cs

│   ├── README.md

│   ├── Models

│   │   └── HardwareStats.cs

│   ├── Services

│   │   ├── HardwareMonitorService.cs

│   │   └── IHardwareMonitorService.cs

│   └── Visitors

│       └── UpdateVisitor.cs

└── torrent-dashboard

    ├── .eslintrc.json

    ├── .gitignore

    ├── banner.png

    ├── eslint.config.mjs

    ├── jsvectormap.d.ts

    ├── LICENSE

    ├── next.config.ts

    ├── package-lock.json

    ├── package.json

    ├── postcss.config.js

    ├── prettier.config.js

    ├── README.md

    ├── tsconfig.json

    ├── public

    │   └── images

    │       ├── favicon.ico

    │       ├── brand/

    │       ├── cards/

    │       ├── carousel/

    │       ├── chat/

    │       ├── country/

    │       ├── error/

    │       ├── grid-image/

    │       ├── icons/

    │       ├── logo/

    │       ├── product/

    │       ├── shape/

    │       ├── task/

    │       ├── user/

    │       └── video-thumb/

    └── src

        ├── middleware.ts

        ├── svg.d.ts

        ├── app

        │   ├── favicon.ico

        │   ├── globals.css

        │   ├── layout.tsx

        │   ├── not-found.tsx

        │   ├── page.tsx

        │   ├── (full-width-pages)/

        │   ├── api/

        │   ├── hardware-monitor/

        │   ├── login/

        │   ├── traffic/

        │   └── warnings/

        ├── components

        │   ├── LastUpdateInfo.tsx

        │   ├── Navbar.tsx

        │   ├── RefreshButton.tsx

        │   ├── Toast.tsx

        │   ├── auth/

        │   ├── calendar/

        │   ├── charts/

        │   ├── common/

        │   ├── ecommerce/

        │   ├── example/

        │   ├── form/

        │   ├── hardware/

        │   ├── header/

        │   ├── tables/

        │   ├── ui/

        │   ├── user-profile/

        │   └── videos/

        ├── context

        │   ├── SidebarContext.tsx

        │   ├── ThemeContext.tsx

        │   └── ToastContext.tsx

        ├── hooks

        │   ├── useGoBack.ts

        │   ├── useHardwareStats.ts

        │   └── useModal.ts

        ├── icons

        │   ├── index.tsx

        │   └── ... (nombreux fichiers .svg)

        ├── layout

        │   ├── AppHeader.tsx

        │   ├── AppSidebar.tsx

        │   ├── Backdrop.tsx

        │   └── SidebarWidget.tsx

        ├── lib

        │   └── api.ts

        └── types

            └── tracker.ts

    </project_files>

</docs>



# Detailed task description & rules

Your goal is to analyze the provided code and requirements to propose a **Robust Architecture Refactor** and then implement the changes.



**Constraint Checklist & Confidence Score:**

1.  **Hardware Monitoring:**

    -   Evaluate if "HWMonitor" is the best tool. If not, propose a better alternative (e.g., a Python agent like `psutil`, Glances API, or a Promethus/Grafana exporter).

    -   Address the latency/security of sending hardware stats to a web dashboard.

2.  **Scraping Engine:**

    -   The scraper must handle login sessions securely.

    -   It must be modular to easily add new torrent sites from {{TARGET_SITES}}.

    -   Consider anti-scraping protections (User-Agent rotation, etc.).

3.  **Architecture:**

    -   Critique the Vercel -> OVH flow. Is it necessary?

    -   If a self-hosted Dockerized approach (Monolith or Microservices on the OVH server) is better for performance and data privacy, suggest it.

4.  **Security:**

    -   Ensure the "simple login" mechanism is secure enough for personal data.



**Strict Rules:**

-   Do NOT preserve code just because it exists. If it's bad, delete it.

-   Prioritize "Functioning" over "Complex".

-   If switching to a Python backend (FastAPI/Flask) is better for the hardware/scraping logic, recommend it.



# Examples

<example>

    **Bad Response:** "I can update your React components. Here is the code for the button."

    **Good Response:** "The current architecture using Vercel serverless functions for hardware monitoring is inefficient due to execution time limits. I recommend moving the backend entirely to your OVH server using Docker. Here is a proposed architecture diagram using a Python agent for stats and a Node.js scraper..."

</example>



# Conversation history

N/A - Start of the audit.



# Immediate task description

1.  **Audit:** Analyze the provided code and the goal. List the top 3 architectural bottlenecks.

2.  **Proposal:** Propose a "Dream Stack" refactor. (e.g., T3 Stack, or Python Backend + React Frontend, Dockerized). Explain *why* it is better for torrent scraping and hardware monitoring.

3.  **Plan:** Outline the steps to migrate/rewrite the application, including how we will handle the new torrent sites.



# Thinking step by step

1.  First, I will assess the feasibility of scraping the requested sites (checking for common protections).

2.  Second, I will evaluate the current method of retrieving hardware stats. Is it pushing data or being pulled?

3.  Third, I will design a data schema that unifies torrent stats and hardware stats.

4.  Finally, I will present the refactor plan.



# Output formatting

Output as Markdown. Use clear headings. Use Code blocks for the folder structure and specific logic examples.



# Prefilled response

<response>

Here is my analysis of your Dashboard project. Based on the requirement for real-time hardware monitoring and scraping, I believe a structural change is necessary...