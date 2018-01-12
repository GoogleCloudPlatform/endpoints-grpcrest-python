# Copyright 2018 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from concurrent import futures
import sys
import time
import grpc
import uuid

import guestbook_pb2
import guestbook_pb2_grpc

DEFAULT_PORT = 8000


class Guestbook(guestbook_pb2_grpc.GuestbookServicer):
    def __init__(self):
        self.posts = []
        self.posts_by_id = {}

        # Add some initial content
        self.__add('First post', 'This is the first post')
        self.__add('Second post', 'This is the second post')

    def __add(self, title, body):
        post = guestbook_pb2.Post(title=title, body=body, id=uuid.uuid4().hex)
        self.posts.append(post)
        self.posts_by_id[post.id] = post

    def AddPost(self, request, context):
        """Submit a post to the guestbook."""
        if not request.title or not request.body:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Invalid arguments')
            return guestbook_pb2.AddPostResponse()

        self.__add(request.title, request.body)
        print('AddPost called [%s] %s' % (post.id, post.title))

        return guestbook_pb2.AddPostResponse(id=post.id)

    def UpdatePost(self, request, context):
        """Modify an existing post, identified by its ID."""
        post = self.posts_by_id.get(request.id) if request.id else None
        if not post:
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details('Not found')
            return guestbook_pb2.UpdatePostResponse()

        post.title = request.title
        post.body = request.body

        print('UpdatePost called [%s] %s' % (post.id, post.title))

        return guestbook_pb2.UpdatePostResponse()

    def ListPosts(self, request, context):
        """List exising posts and optionally allow paging."""
        page = abs(request.page) if request.page else 0
        page_size = abs(request.page_size) if request.page_size else 10

        print('ListPosts called (page %d, size %d)' % (page, page_size))

        return guestbook_pb2.ListPostsResponse(
            posts=self.posts[page * page_size: (page + 1) * page_size]
        )

    def GetHealth(self, request, context):
        import socket
        return guestbook_pb2.GetHealthResponse(hostname=socket.gethostname())


def server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    guestbook_pb2_grpc.add_GuestbookServicer_to_server(Guestbook(), server)
    server.add_insecure_port('[::]:%d' % DEFAULT_PORT)
    server.start()
    try:
        while True:
            _ONE_DAY_IN_SECONDS = 60 * 60 * 24
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


def client(host, port):
    channel = grpc.insecure_channel('%s:%d' % (host, port))

    stub = guestbook_pb2_grpc.GuestbookStub(channel)
    for post in stub.ListPosts(guestbook_pb2.ListPostsRequest()).posts:
        print('[%s] %s\n%s\n' % (post.id, post.title, post.body))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--client':
        client(
            sys.argv[2] if len(sys.argv) > 2 else 'localhost',
            int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_PORT)
    else:
        server()
