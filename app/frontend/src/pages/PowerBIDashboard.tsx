import React from "react";

const PowerBIDashboard: React.FC = () => {
    return (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: 32 }}>
            <h1>Power BI Dashboard</h1>
            <iframe
                title="Sales & Returns Sample v201912"
                width="600"
                height="373.5"
                src="https://app.powerbi.com/view?r=eyJrIjoiOGRlMGQ1NDAtMDBkNC00OTM0LWFmZGQtMWI4MDljMmM4MTRiIiwidCI6IjM3M2U5MGQyLWQ5YTMtNDNiNS04MzJlLWM4ZTk4NDdhNzlmOCIsImMiOjEwfQ%3D%3D"
                frameBorder="0"
                allowFullScreen={true}
                style={{ border: 0 }}
            ></iframe>
        </div>
    );
};

export default PowerBIDashboard;
