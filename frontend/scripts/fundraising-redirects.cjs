// Keep the game's historical entry aliases and old payment returns intact.
const oldGameEntries = new Set(["/organize-board-fundraising-game","/organize-board-fundraising-game/apply","/game/upgrade","/game/start","/board-fundraising/start","/game/demonstration"]);
const productEntries = new Set(["/recruit","/recruit/start","/recruit/walkthrough","/strategic-planning","/strategic-planning/start","/strategic-planning/video","/board-recommitment","/board-recommitment/start","/board-recommitment/video"]);
module.exports = function redirect(req,res) {
 if(!["GET","HEAD"].includes(req.method))return false;
 const url=new URL(req.url,"http://localhost");const pathname=url.pathname.replace(/\/+$/,"")||"/";
 const session=url.searchParams.get("session_id");
 if(session&&(productEntries.has(pathname)||oldGameEntries.has(pathname))){res.writeHead(302,{Location:"/purchase/success?session_id="+encodeURIComponent(session),"Cache-Control":"no-cache"});res.end();return true;}
 const destination=pathname==="/board-fundraising"?"/board-fundraising-game"+url.search:oldGameEntries.has(pathname)?"/how-the-fundraising-game-works":null;
 if(!destination)return false;
 res.writeHead(301,{Location:destination,"Cache-Control":"no-cache"});res.end();return true;
};
