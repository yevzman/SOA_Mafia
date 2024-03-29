# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from . import mafiaRPC_pb2 as mafiaRPC__pb2


class MafiaClientStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.GetNewPlayerId = channel.unary_unary(
                '/mafia.MafiaClient/GetNewPlayerId',
                request_serializer=mafiaRPC__pb2.Request.SerializeToString,
                response_deserializer=mafiaRPC__pb2.PlayerId.FromString,
                )
        self.Subscribe = channel.unary_stream(
                '/mafia.MafiaClient/Subscribe',
                request_serializer=mafiaRPC__pb2.Player.SerializeToString,
                response_deserializer=mafiaRPC__pb2.Response.FromString,
                )
        self.Unsubscribe = channel.unary_unary(
                '/mafia.MafiaClient/Unsubscribe',
                request_serializer=mafiaRPC__pb2.Player.SerializeToString,
                response_deserializer=mafiaRPC__pb2.Response.FromString,
                )
        self.SendVote = channel.unary_unary(
                '/mafia.MafiaClient/SendVote',
                request_serializer=mafiaRPC__pb2.VoteRequest.SerializeToString,
                response_deserializer=mafiaRPC__pb2.VoteResponse.FromString,
                )


class MafiaClientServicer(object):
    """Missing associated documentation comment in .proto file."""

    def GetNewPlayerId(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Subscribe(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Unsubscribe(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SendVote(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_MafiaClientServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'GetNewPlayerId': grpc.unary_unary_rpc_method_handler(
                    servicer.GetNewPlayerId,
                    request_deserializer=mafiaRPC__pb2.Request.FromString,
                    response_serializer=mafiaRPC__pb2.PlayerId.SerializeToString,
            ),
            'Subscribe': grpc.unary_stream_rpc_method_handler(
                    servicer.Subscribe,
                    request_deserializer=mafiaRPC__pb2.Player.FromString,
                    response_serializer=mafiaRPC__pb2.Response.SerializeToString,
            ),
            'Unsubscribe': grpc.unary_unary_rpc_method_handler(
                    servicer.Unsubscribe,
                    request_deserializer=mafiaRPC__pb2.Player.FromString,
                    response_serializer=mafiaRPC__pb2.Response.SerializeToString,
            ),
            'SendVote': grpc.unary_unary_rpc_method_handler(
                    servicer.SendVote,
                    request_deserializer=mafiaRPC__pb2.VoteRequest.FromString,
                    response_serializer=mafiaRPC__pb2.VoteResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'mafia.MafiaClient', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class MafiaClient(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def GetNewPlayerId(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/mafia.MafiaClient/GetNewPlayerId',
            mafiaRPC__pb2.Request.SerializeToString,
            mafiaRPC__pb2.PlayerId.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Subscribe(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(request, target, '/mafia.MafiaClient/Subscribe',
            mafiaRPC__pb2.Player.SerializeToString,
            mafiaRPC__pb2.Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Unsubscribe(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/mafia.MafiaClient/Unsubscribe',
            mafiaRPC__pb2.Player.SerializeToString,
            mafiaRPC__pb2.Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def SendVote(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/mafia.MafiaClient/SendVote',
            mafiaRPC__pb2.VoteRequest.SerializeToString,
            mafiaRPC__pb2.VoteResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
