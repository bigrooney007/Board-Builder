import { useEffect, useState } from "react";
import axios from "axios";
import { BfgShell } from "./gameShared";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const READY = [
  "Yes, we are ready to organize the Board Fundraising Game.",
  "I am ready, but I need to confirm with my board.",
  "We are interested, but we need to discuss it as a board first.",
];

export default function FacilitatedGameApplicationPage() {
  const [form,setForm]=useState({organization_name:"",name:"",position:"",email:"",board_members:"",mission:"",website:"",readiness:""});
  const [busy,setBusy]=useState(false); const [error,setError]=useState(""); const [booking,setBooking]=useState("");
  useEffect(()=>{document.title="Apply | Board Fundraising Game";},[]);
  const set=(key)=>(e)=>setForm(v=>({...v,[key]:e.target.value}));
  const submit=async(e)=>{e.preventDefault();setBusy(true);setError("");try{
    const r=await axios.post(`${API}/facilitated-game-application`,{...form,board_members:Number(form.board_members)});
    setBooking(r.data.booking_url);
  }catch(err){setError(err.response?.data?.detail || "We could not submit your application. Please try again.");setBusy(false);}};

  return <BfgShell><main className="facilitated-page" data-testid="facilitated-application-page">
    <section className="facilitated-hero">
      <span className="bfg-badge">BOARD FUNDRAISING GAME APPLICATION</span>
      <h1>Let's See If The Facilitated Board Fundraising Game Is Right For Your Organization.</h1>
      <p>Tell me a little about your organization and your board. Once you submit the application, you can book a call with me to discuss your Board Fundraising Game.</p>
    </section>
    <section className="facilitated-section">
      <div className="facilitated-offer">
      {booking ? <>
        <p className="facilitated-eyebrow">APPLICATION RECEIVED</p>
        <h2>Now Book Your Call With Rooney.</h2>
        <p>I have your application. Choose a time below so we can talk about your organization, your board and whether the Board Fundraising Game is the right next step.</p>
        <a className="bfg-btn bfg-btn-primary facilitated-cta" href={booking} data-testid="facilitated-book-call">BOOK MY CALL WITH ROONEY</a>
      </> : <form onSubmit={submit} className="facilitated-application-form">
        <h2>Apply To Organize Your Board Fundraising Game</h2>
        <label className="field"><span>Organization Name *</span><input required value={form.organization_name} onChange={set("organization_name")} /></label>
        <label className="field"><span>Your Name *</span><input required value={form.name} onChange={set("name")} /></label>
        <label className="field"><span>Your Position / Role *</span><input required value={form.position} onChange={set("position")} /></label>
        <label className="field"><span>Email Address *</span><input required type="email" value={form.email} onChange={set("email")} /></label>
        <label className="field"><span>How Many Board Members Do You Currently Have? *</span><input required type="number" min="1" max="500" value={form.board_members} onChange={set("board_members")} /></label>
        <label className="field"><span>What Is Your Organization's Mission? *</span><textarea required rows="5" value={form.mission} onChange={set("mission")} /></label>
        <label className="field"><span>Organization Website *</span><input required type="text" placeholder="https://yourorganization.org" value={form.website} onChange={set("website")} /></label>
        <fieldset className="field choice-field"><legend>Are You And Your Board Ready To Participate In The Board Fundraising Game? *</legend>
          <div className="choice-grid">{READY.map(x=><label className={`choice ${form.readiness===x?"selected":""}`} key={x}><input required type="radio" name="readiness" value={x} checked={form.readiness===x} onChange={set("readiness")} /><span>{x}</span></label>)}</div>
        </fieldset>
        {error&&<p className="bfg-error">{typeof error==="string"?error:"Please check the form and try again."}</p>}
        <button className="bfg-btn bfg-btn-primary facilitated-cta" disabled={busy} type="submit">{busy?"SUBMITTING…":"SUBMIT MY APPLICATION"}</button>
        <small>No payment is required to apply. After submitting, you will be able to book a call with Rooney Akpesiri.</small>
      </form>}
      </div>
    </section>
  </main></BfgShell>;
}
