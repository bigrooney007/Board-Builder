export const ApplicantError = ({ name, message }) => message ? <p className="field-error" data-testid={`applicant-${name}-error`}>{message}</p> : null;

export const ApplicantText = ({ name, label, value, update, error, required = true, type = "text", placeholder, helper }) => (
  <label className="field" data-testid={`applicant-${name}-field`}><span>{label}{required && <b> *</b>}</span><input type={type} value={value} placeholder={placeholder} onChange={(event) => update(name, event.target.value)} data-testid={`applicant-${name}-input`} />{helper && <small data-testid={`applicant-${name}-helper`}>{helper}</small>}<ApplicantError name={name} message={error} /></label>
);

export const ApplicantTextarea = ({ name, label, value, update, error, placeholder }) => (
  <label className="field" data-testid={`applicant-${name}-field`}><span>{label} <b>*</b></span><textarea rows="4" value={value} placeholder={placeholder} onChange={(event) => update(name, event.target.value)} data-testid={`applicant-${name}-textarea`} /><ApplicantError name={name} message={error} /></label>
);

export const ApplicantSelect = ({ name, label, value, update, error, options }) => (
  <label className="field" data-testid={`applicant-${name}-field`}><span>{label} <b>*</b></span><select value={value} onChange={(event) => update(name, event.target.value)} data-testid={`applicant-${name}-select`}><option value="">Select one</option>{options.map((option) => <option value={option} key={option}>{option}</option>)}</select><ApplicantError name={name} message={error} /></label>
);

export const ApplicantChoices = ({ name, label, value, update, error, options, multiple = false }) => {
  const select = (option) => multiple
    ? update(name, value.includes(option) ? value.filter((item) => item !== option) : [...value, option])
    : update(name, option);
  return <fieldset className="field choice-field" data-testid={`applicant-${name}-field`}><legend>{label} <b>*</b></legend><div className="choice-grid">{options.map((option, index) => { const selected = multiple ? value.includes(option) : value === option; return <label className={`choice ${selected ? "selected" : ""}`} key={option}><input type={multiple ? "checkbox" : "radio"} name={multiple ? undefined : name} checked={selected} onChange={() => select(option)} data-testid={`applicant-${name}-option-${index + 1}`} /><span>{option}</span></label>; })}</div><ApplicantError name={name} message={error} /></fieldset>;
};

export const ApplicantConsent = ({ name, text, checked, update, required = false, error }) => <><label className={`confirmation-check ${checked ? "selected" : ""}`} data-testid={`applicant-${name}-field`}><input type="checkbox" checked={checked} onChange={(event) => update(name, event.target.checked)} data-testid={`applicant-${name}-checkbox`} /><span>{text}{required && <b> *</b>}</span></label><ApplicantError name={name} message={error} /></>;

export const ApplicantActions = ({ back, next, final = false, submitting = false }) => <div className="form-actions">{back && <button className="button button-back" type="button" onClick={back} data-testid="applicant-back-button">Back</button>}<button className="button" type="button" onClick={next} disabled={submitting} data-testid={final ? "save-applicant-profile-button" : "applicant-next-button"}>{submitting ? "Saving…" : final ? "Save My Board Applicant Profile" : "Next"}</button></div>;