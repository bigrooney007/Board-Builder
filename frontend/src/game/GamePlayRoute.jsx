import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import GamePlayPage from "./GamePlayPage";
import GameFivePlayPage from "./GameFivePlayPage";

export default function GamePlayRoute() {
  const { token } = useParams();
  const [version, setVersion] = useState(null);
  useEffect(() => {
    let active = true;
    axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/game/play/${token}`)
      .then(({ data }) => { if (active) setVersion(Number(data.member?.game_version || 4)); })
      .catch(() => { if (active) setVersion(-1); });
    return () => { active = false; };
  }, [token]);
  if (version === null) return <div className="bfg" style={{ minHeight: "100vh" }} />;
  if (version === -1) return <div className="bfg"><main className="bfg-flow"><h1>This game link is not available.</h1></main></div>;
  return version === 5 ? <GameFivePlayPage /> : <GamePlayPage />;
}
