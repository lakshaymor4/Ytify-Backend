from fastapi import APIRouter, FastAPI
from services import setup_yt
from services import transfer_service
import jwt
import uuid
import config
import jsonify
router = APIRouter()


@router.post("/setyt", tags=["yt_header"])
async def setYT(request: dict):
   try:
       header = request.get("header")
       token = request.get("token")
       
       if not all([header, token]):
           return {"status": "error", "message": "Missing required fields"}
       
       jwt_decode = jwt.decode(token, config.SECRET, algorithms=["HS256"])
       
      
       setup_result = setup_yt(jwt_decode["session_id"], header)
       
       if setup_result["success"]:
           return {"status": "success", "message": setup_result["message"]}
       else:
           return {"status": "error", "message": setup_result["message"]}
       
   except jwt.InvalidTokenError:
       return {"status": "error", "message": "Invalid token"}
   except KeyError:
       return {"status": "error", "message": "Invalid JWT payload - missing session_id"}
   except Exception as e:
       return {"status": "error", "message": str(e)}

@router.post('/authenticate')
async def authenticate(request: dict):
    try:
        jwt_decode = jwt.decode(token, config.SECRET, algorithms=["HS256"])
        manager = transfer_service.get_transfer_manager()
        success, message = manager.authenticate_services(jwt_decode.uuid)
        token = request.get("token")
        if success:
            
           
            payload = {
                'uuid' : jwt_decode.uuid,
                'auth': True
            }
            token = jwt.encode(payload, config.SECRET, algorithm="HS256")
            return jsonify({
                'success': True,
                'jwt': token,
                'message':message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Authentication error: {str(e)}'
        }), 500



