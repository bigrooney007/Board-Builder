import { useEffect, useState } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const useFlowVideo = (key) => {
  const [video, setVideo] = useState(null);
  useEffect(() => {
    axios.get(`${API}/flow-videos`)
      .then((r) => setVideo((r.data.videos || []).find((v) => v.key === key) || null))
      .catch(() => {});
  }, [key]);
  return video;
};
