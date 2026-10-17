const retired = new Set(["/recruit","/recruit/start","/recruit/walkthrough","/strategic-planning","/strategic-planning/start","/strategic-planning/video","/board-recommitment","/board-recommitment/start","/board-recommitment/video","/organize-board-fundraising-game","/organize-board-fundraising-game/apply","/board-fundraising-game","/game/upgrade","/game/start","/board-fundraising/start","/game/demonstration"]);
module.exports = function redirect(req,res) {
 if(!["GET","HEAD"].includes(req.method))return false;
 const url=new URL(req.url,"http://localhost");const pathname=url.pathname.replace(/\/+$/,"")||"/";
 if(!retired.has(pathname))return false;
 const session=url.searchParams.get("session_id");
 const destination=session?"/purchase/success?session_id="+encodeURIComponent(session):pathname==="/board-fundraising-game"?"/":"/how-the-fundraising-game-works";
 res.writeHead(session?302:301,{Location:destination,"Cache-Control":"no-cache"});res.end();return true;
};
