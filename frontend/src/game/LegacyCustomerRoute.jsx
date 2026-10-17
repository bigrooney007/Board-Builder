import { Navigate,useLocation } from "react-router-dom";
import { useMemberAuth } from "@/member/MemberAuthContext";
export default function LegacyCustomerRoute({children,entitlement}){
 const {member,loading}=useMemberAuth();const location=useLocation();
 if(loading)return <p>Checking your saved customer access…</p>;
 const session=new URLSearchParams(location.search).get("session_id");
 if(session)return <Navigate to={"/purchase/success?session_id="+encodeURIComponent(session)} replace/>;
 if(member?.entitlements?.includes(entitlement))return children;
 return <Navigate to="/how-the-fundraising-game-works" replace/>;
}
