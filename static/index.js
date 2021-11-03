const INIT = 0
const READY = 1
const PLAYING = 2
const SWITCH = 3

const SETUP = 0
const PLAY = 1
const PAUSE = 2
const TEARDOWN = 3
const SETTIME = 5

var rtspSeq = 0
var sessionID = 0
var requestSend = -1
var frameNbr = 0
var state = INIT
var totalFrame = 0
var videoName = ''
const ttT = document.getElementById('totalTime')
const rT = document.getElementById('remainingTime')
const listVideo = document.getElementById('selectVideo')

var socket = io.connect('http://127.0.0.1:5000');

socket.on('listVideo', function(list) {
  for (const e in list) {
    var video = document.createElement('option')
    video.text = list[e]
    video.value = list[e]
    listVideo.add(video)
  }
  listVideo.value = videoName = list[0]
});  

socket.on('rtpPacket', function(msg) {
  const blob = new Blob( [ msg ] );
  const url = URL.createObjectURL( blob );
  var img = document.getElementById('cachePng')
  img.src = url
  frameNbr += 1
  if (frameNbr % 10 === 0) {
    rT.textContent = frameNbr / 20
  }
});

async function changeVideo() {
  var video = document.getElementById('selectVideo')
  videoName = video.value
  await stop()
  await play()
}

async function setup() {
  if (state === INIT) {
    rtspSeq = 0
    frameNbr = 0
    teardownAcked = 0
    await sendRrspRequest(SETUP)
  }
}

async function play() {
  if (state === INIT) {
    await setup()
  }
  if (state === INIT || state === READY) {
    await sendRrspRequest(PLAY) 
  }
}

async function pause() {
  if (state === PLAYING) {
    await sendRrspRequest(PAUSE)
  }
}

async function stop() {
  if (state === PLAYING) {
    await pause()
  } 
  if (self.state == READY) {
    await sendRrspRequest(TEARDOWN)
  }
}

async function forward() {
  if (state === PLAYING || state === READY) {
    frameNbr += 20 * 2
    if (frameNbr > totalFrame) {
      frameNbr = totalFrame
    }
    sendRrspRequest(SETTIME)
  }
}

async function backward() {
  if (state === PLAYING || state === READY) {
    frameNbr -= 20 * 2
    if (frameNbr < 0) {
      frameNbr = 0
    }
    sendRrspRequest(SETTIME)
  }
}

function asyncEmit(eventName, data) {
  return new Promise(function (resolve, reject) {
    socket.emit(eventName, data);
    socket.on(eventName, result => {
      socket.off(eventName);
      resolve(result);
    });
    setTimeout(reject, 1000);
  });
}

async function sendRrspRequest(requestCode) {
  var request = ""
  rtspSeq += 1
  if (requestCode === SETUP) {
    request += "SETUP " + videoName + " RTSP/1.0\n"
    request += "CSeq: " + rtspSeq + "\n"
  } else {
    if (requestCode === PLAY) {
      request += "PLAY "
    } else if (requestCode === PAUSE) {
      request += "PAUSE "
    } else if (requestCode === TEARDOWN) {
      request += "TEARDOWN "
    } else if (requestCode === SETTIME) {
      request += "SETTIME "
    }
    request += videoName + ' RTSP/1.0\n'
    request += 'CSeq: ' + rtspSeq + '\n'
    request += 'Session: ' + sessionID 
    if (requestCode === SETTIME) {
      request += "\nFRAME: " + frameNbr
    }
  }
  requestSend = requestCode
  response = await asyncEmit('rtspRequest', request)
  await parseRtspReply(response)
}

async function parseRtspReply(mess) {
  const response = mess.split('\n')
  const code = Number(response[0].split(' ')[1])
  if (code === 200) {
    const seq = Number(response[1].split(' ')[1])
    if (seq === rtspSeq) {
      const session = Number(response[2].split(' ')[1])
      if (requestSend === SETUP) {
        sessionID = session
        state = READY
      } else {
        if (sessionID !== session) return;
        if (requestSend === PLAY) {
          state = PLAYING
          totalFrame = Number(response[3].split(' ')[1])
          ttT.textContent = '/' + totalFrame / 20 + ' second'
        }
        if (requestSend === PAUSE) {
          state = READY
        }
        if (requestSend === TEARDOWN) {
          state = INIT
          teardownAcked = 1
        } 
      }
    }
  }
  else if (code === 404) {
    console.log('File not found!')
  }
  else if (code === 500) {
    console.log('Connection error!')
  }
}
