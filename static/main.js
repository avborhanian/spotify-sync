WebSocket.prototype.send_j = function(json) {
    this.send(JSON.stringify(json));
}

var ws = new WebSocket("ws://localhost:3000/socket");

ws.onopen = function() {
    ws.send_j({"action": "create_room", "room_name": "test"});
    ws.send_j({"action": "join_room", "room_name": "test"});
}

ws.onmessage = function(e) {
    data = JSON.parse(e.data);
    console.log(data);
}

function limitSize(string, max_length) {
    if (string.length > max_length) {
        string = string.substring(0, max_length);
        if (string.endsWith(",")) {
            string = string.substring(0, string.length - 1);
        }
        string = string.concat("...");
    }
    return string;
}

function searchQuery() {
    var max_artist_len = 45;
    var search = document.querySelector("#searchForm");
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "http://localhost:3000/api/search?q=" + search.value, true);
    xhr.onload = function(e) {
        document.getElementById("searchList").innerHTML = '';
        var tracks = JSON.parse(this.responseText).tracks.items;
        for (var i = 0; i < tracks.length; i++) {
            var track = tracks[i];
            var elem = document.createElement("div");
            elem.className = "row m-3"
            elem.style.fontSize = ".9rem";
            var artists = track.artists.map(function(a) {
                return a.name
            }).join(", ");
            artists = limitSize(artists, max_artist_len);
            elem.innerHTML = ("<div class='col-2'><img src='" + track.album.images[2].url + "'></img></div><div class='col-10'><div>Artist: " + 
                artists + "</div><div>Song: " + limitSize(track.name, 45) + "</div><div>Album: " + 
                limitSize(track.album.name, 45) + "</div></div>");
            document.getElementById("searchList").appendChild(elem);
        }
    }
    xhr.send();
}