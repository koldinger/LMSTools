"""
Simple python class definitions for interacting with Logitech Media Server.
This code uses the JSON interface.
"""
import urllib.request
import urllib.error
import json

from .player import LMSPlayer

#from icecream import ic

class LMSConnectionError(Exception):
    pass


class LMSServer:
    """
    Class for Logitech Media Server.

    Provides access via JSON interface. As the class uses the JSON interface, no active connections are maintained.

    :type host: str
    :param host: address of LMS server (default "localhost")
    :type port: int
    :param port: port for the web interface (default 9000)


    """

    def __init__(self, host="localhost", port=9000):
        self.host = host
        self.port = port
        self._version = None
        self.id = 1
        self.web = f"http://{host}:{port}/"
        self.url = f"http://{host}:{port}/jsonrpc.js"

    def request(self, player="-", params=None):
        """
        Perform a request to the server.

        :type player: (str)
        :param player: MAC address of a connected player. Alternatively, "-" can be used for server level requests.
        :type params: (str, list)
        :param params: Request command

        """
        req = urllib.request.Request(self.url)
        req.add_header("Content-Type", "application/json")


        if type(params) == str:
            params = params.split()

        cmd = [player, params]

        data = {"id": self.id,
                "method": "slim.request",
                "params": cmd}

        try:
            response = urllib.request.urlopen(req, bytes(json.dumps(data), "utf8"))
            self.id += 1
            return json.loads(response.read())["result"]

        except urllib.error.URLError:
            raise LMSConnectionError("Could not connect to server.")

        except Exception:
            return None

    def get_players(self):
        """
        Return a list of currently connected Squeezeplayers.

        :rtype: list
        :returns: list of LMSPlayer instances

        ::

            >>>server.get_players()
            [LMSPlayer: Living Room (40:40:40:40:40:40),
             LMSPlayer: PiRadio (41:41:41:41:41:41),
             LMSPlayer: elParaguayo's Laptop (42:42:42:42:42:42)]

        """
        self.players = []
        player_count = self.get_player_count()
        for i in range(player_count):
            player = LMSPlayer.from_index(i, self)
            self.players.append(player)
        return self.players

    def get_player_count(self):
        """
        Get the number of players.

        :rtype: int
        :returns: number of connected players

        ::

            >>>server.get_player_count()
            3

        """
        try:
            # Get the count, and make sure it's an int.
            # Bug in LMS, when they player count is 0, it returns a string '0', instead of int 0.
            count = int(self.request(params="player count ?")["_count"])
        except:
            count = 0

        return count

    def get_sync_groups(self):
        """
        :rtype: list
        :returns: list of syncgroups. Each group is a list of references of the members.

        ::

            >>>server.get_sync_groups()
            [[u'40:40:40:40:40:40', u'41:41:41:41:41:41']]

        """
        groups = self.request(params="syncgroups ?")
        syncgroups = [x.get("sync_members","").split(",") for x in groups.get("syncgroups_loop",dict())]
        return syncgroups

    def show_players_sync_status(self):
        """
        :rtype: dict
        :returns: dictionary (see attributes below)
        :attr group_count: (int) Number of sync groups
        :attr player_count: (int) Number of connected players
        :attr players: (list) List of players (see below)

        Player object (dict)

        :attr name: Name of player
        :attr ref: Player reference
        :attr sync_index: Index of sync group (-1 if not synced)

        ::

            >>>server.show_players_sync_status()
            {'group_count': 1,
             'player_count': 3,
             'players': [{'name': u'Living Room',
                          'ref': u'40:40:40:40:40:40',
                          'sync_index': 0},
                          {'name': u'PiRadio',
                          'ref': u'41:41:41:41:41:41',
                          'sync_index': 0},
                          {'name': u"elParaguayo's Laptop",
                          'ref': u'42:42:42:42:42:42',
                          'sync_index': -1}]}

        """
        players = self.get_players()
        groups = self.get_sync_groups()

        all_players = []

        for player in players:
            item = {}
            item["name"] = player.name
            item["ref"] = player.ref
            index = [i for i, g in enumerate(groups) if player.ref in g]
            if index:
                item["sync_index"] = index[0]
            else:
                item["sync_index"] = -1
            all_players.append(item)

        sync_status = {}
        sync_status["group_count"] = len(groups)
        sync_status["player_count"] = len(players)
        sync_status["players"] = all_players

        return sync_status

    def sync(self, master, slave):
        """
        :type master: (ref)
        :param master: Reference of the player to which you wish to sync another player
        :type slave: (ref)
        :param slave: Reference of the player which you wish to sync to the master

        Sync squeezeplayers.
        """
        self.request(player=master, params=["sync", slave])


    def ping(self):
        """
        Method to test if server is active.

        :rtype: bool
        :returns: True if server is alive, False if server is unreachable

        ::

            >>>server.ping()
            True

        """
        try:
            self.request(params="ping")
            return True
        except LMSConnectionError:
            return False

    @property
    def version(self):
        """
        Get the version of the server.

        :attr version: Version number of server Software

        ::

            >>>server.version
            u'7.9.0'
        """
        if self._version is None:
            self._version = self.request(params="version ?")["_version"]

        return self._version

    def rescan(self, mode="fast"):
        """
        Trigger rescan of the media library.

        :type mode: str
        :param mode: Mode can be 'fast' for update changes on library, 'full' for complete library scan and 'playlists' for playlists scan only
        """
        is_scanning = True
        try:
            is_scanning = bool(self.request("rescan ?")["_rescan"])
        except:
            pass

        if not is_scanning:
            if mode == "fast":
                return self.request(params="rescan")
            if mode == "full":
                return self.request(params="wipecache")
            if mode == "playlists":
                return self.request(params="rescan playlists")
        return ""

    @property
    def rescanprogress(self):
        """
        Get the progress of the current rescan.

        :attr rescanprogress: current rescan progress
        """
        return self.request(params="rescanprogress")["_rescan"]
