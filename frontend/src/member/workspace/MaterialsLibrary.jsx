import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Copy, Printer } from "lucide-react";
import { memberApi } from "../api";
import { MemberShell } from "../MemberShell";
import { printText } from "./MaterialCard";

const MODULE_NAMES = { 2: "Module 2 — Recruitment Strategy", 3: "Module 3 — Launch Your Recruitment Campaign", 4: "Module 4 — Interview Your Applicants", 5: "Module 5 — References and Background Checks", 6: "Module 6 — Onboard Your New Board Members" };

export const MaterialsLibraryPage = () => {
  const [materials, setMaterials] = useState([]);
  const [openId, setOpenId] = useState("");
  useEffect(() => { memberApi.get("/workspace/materials").then((response) => setMaterials(response.data.materials)).catch(() => {}); }, []);
  const grouped = {};
  materials.forEach((material) => { (grouped[material.module] = grouped[material.module] || []).push(material); });
  return (
    <MemberShell>
      <main className="member-page" data-testid="materials-library-page">
        <header className="member-page-heading">
          <Link className="module-breadcrumb" to="/app/recruitment/self-guided"><ArrowLeft size={15} /> Self-Guided Recruitment System</Link>
          <h1>My Recruitment Materials</h1>
          <p>Every generated resource stays available here, organized by module, with full version history.</p>
        </header>
        {materials.length === 0 && <div className="member-card"><p>No materials yet. Generate materials inside the course modules.</p></div>}
        {Object.keys(grouped).sort().map((module) => (
          <section className="member-card" key={module}>
            <h2>{MODULE_NAMES[module] || `Module ${module}`}</h2>
            {grouped[module].map((material) => {
              const version = material.versions.find((v) => v.version === material.current_version);
              return (
                <div className="library-item" key={material.material_id} data-testid={`library-item-${material.type}-${material.application_id || "org"}`}>
                  <button className="library-item-head" onClick={() => setOpenId(openId === material.material_id ? "" : material.material_id)}>
                    <strong>{material.title}</strong>
                    <span>{material.type}{material.application_id ? " · applicant material" : ""}</span>
                    <span>Created {new Date(material.created_at).toLocaleDateString()} · Updated {new Date(material.updated_at).toLocaleDateString()}</span>
                    <span>Status: {material.status} · {material.versions.length} version{material.versions.length > 1 ? "s" : ""} (Current: v{material.current_version})</span>
                  </button>
                  {openId === material.material_id && version && (
                    <div className="library-item-body">
                      <pre className="material-display">{version.display_text}</pre>
                      <div className="material-actions">
                        <button className="button button-back" onClick={() => navigator.clipboard?.writeText(version.display_text)}><Copy size={14} /> Copy</button>
                        <button className="button button-back" onClick={() => printText(material.title, version.display_text)}><Printer size={14} /> Print / Download PDF</button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </section>
        ))}
      </main>
    </MemberShell>
  );
};
