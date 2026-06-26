function sameOrigin(req){
  const origin=req.headers.origin;
  const host=req.headers.host;
  if(!origin||!host)return true;
  try{return new URL(origin).host===host;}catch{return false;}
}

async function redisCommand(command,key){
  const base=(process.env.UPSTASH_REDIS_REST_URL||process.env.KV_REST_API_URL||"").replace(/\/$/,"");
  const token=process.env.UPSTASH_REDIS_REST_TOKEN||process.env.KV_REST_API_TOKEN;
  if(!base||!token)throw new Error("counter_not_configured");
  const response=await fetch(`${base}/${command}/${encodeURIComponent(key)}`,{
    method:"GET",
    headers:{Authorization:`Bearer ${token}`},
    cache:"no-store"
  });
  const data=await response.json().catch(()=>({}));
  if(!response.ok||data.error)throw new Error(data.error||"redis_error");
  return data.result;
}

module.exports=async function handler(req,res){
  res.setHeader("Cache-Control","no-store, max-age=0");
  res.setHeader("Content-Type","application/json; charset=utf-8");
  if(!sameOrigin(req))return res.status(403).json({error:"forbidden"});
  if(req.method!=="GET"&&req.method!=="POST"){
    res.setHeader("Allow","GET, POST");
    return res.status(405).json({error:"method_not_allowed"});
  }
  try{
    const key="tree-id-trainer:global-visits";
    let count;
    if(req.method==="POST")count=await redisCommand("incr",key);
    else count=await redisCommand("get",key);
    return res.status(200).json({count:Number(count||0)});
  }catch(error){
    const missing=error?.message==="counter_not_configured";
    return res.status(missing?503:500).json({error:missing?"counter_not_configured":"counter_failed"});
  }
};
