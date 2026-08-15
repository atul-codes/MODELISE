import grpc
from concurrent import futures

import pel_pb2
import pel_pb2_grpc

# your already-built inference function
from pel_artifacts.inference import predict_text_policy, predict_image_policy 

class PolicyEnforcementServicer(pel_pb2_grpc.PolicyEnforcementServicer):

    def InspectText(self, request, context):
        result = predict_text_policy(request.text)

        action_map = {
            "ALLOW": pel_pb2.ALLOW,
            "BLOCK": pel_pb2.BLOCK
        }

        return pel_pb2.InspectResponse(
            action=action_map[result["action"]]
        )
    
    def InspectImage(self, request, context):
        result = predict_image_policy(request.image_data)

        action_map = {
            "ALLOW": pel_pb2.ALLOW,
            "BLOCK": pel_pb2.BLOCK
        }

        return pel_pb2.InspectResponse(
            action=action_map[result["action"]]
        )


def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=8)
    )

    pel_pb2_grpc.add_PolicyEnforcementServicer_to_server(
        PolicyEnforcementServicer(),
        server
    )

    server.add_insecure_port("[::]:50051")
    server.start()

    print("PEL gRPC service running on port 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()