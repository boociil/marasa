// const { makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion } = require("baileys")
import { makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion, jidDecode } from 'baileys';
import pino from 'pino';
import chalk from 'chalk';
import readline from 'node:readline';
import {resolve} from 'path';
import {version} from 'os';

import dotenv from 'dotenv';
dotenv.config();

let waSocket = null
// Metode Pairing
const usePairingCode = true

// Promt Input Terminal
async function question(promt) {
    process.stdout.write(promt)
    const r1 = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    })

    return new Promise((resolve) => r1.question("", (ans) => {
        r1.close()
        resolve(ans)
    }))
    
}

const DEBOUNCE_MS = 3_000

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState('./waSocketSesi')
  
  // Versi Terbaru
  const { version, isLatest } = await fetchLatestBaileysVersion()
  console.log(`Using WA v${version.join('.')}, isLatest: ${isLatest}`)

  waSocket = makeWASocket({
    logger: pino({ level: "silent" }),
    printQRInTerminal: !usePairingCode,
    auth: state,
    browser: ['Ubuntu', 'Chrome', '20.0.04'],
    version: version,
    syncFullHistory: false,
    generateHighQualityLinkPreview: true,
    getMessage: async (key) => {
      if (store) {
        const msg = await store.loadMessage(key.remoteJid, key.id)
        return msg?.message || undefined
      }
      return proto.Message.fromObject({})
    }
  })

  // Handle Pairing Code
  if (usePairingCode && !waSocket.authState.creds.registered) {
    try {
      const phoneNumber = await question('☘️ Masukan Nomor Yang Diawali Dengan 62 :\n')
      const code = await waSocket.requestPairingCode(phoneNumber.trim())
      console.log(`🎁 Pairing Code : ${code}`)
    } catch (err) {
      console.error('Failed to get pairing code:', err)
    }
  }
    // Menyimpan Sesi Login
    waSocket.ev.on("creds.update", saveCreds)

    // Informasi Koneksi
    waSocket.ev.on("connection.update", (update) => {
        const { connection, lastDisconnect } = update
        if ( connection === "close") {
            console.log(chalk.red("❌  Koneksi Terputus, Mencoba Menyambung Ulang"))
            connectToWhatsApp()
        } else if ( connection === "open") {
            console.log(chalk.green("✔  Bot Berhasil Terhubung Ke WhatsApp"))
        }
    })

    const messageBuffer = new Map()
    const debounceTimers = new Map()

    // Respon Pesan Masuk
    waSocket.ev.on("messages.upsert", async ({ messages, type }) => {

      const sendMessage = (jid, teks) => waSocket.sendMessage(jid, { text: teks });

      async function repeat_timer(jid_local, isfromMe_local){
        // if(isfromMe_local){
        //   return
        // }
        const allMessages = messageBuffer.get(jid_local)

        try {
          const response = await fetch(process.env.PYTHON_URL, {body : JSON.stringify(allMessages), method: 'POST',  
            headers: {
              Accept: "application/json",
              "Content-Type": "application/json",
          }});
          if (!response.ok) {
            throw new Error(`Response status: ${response.status}`);
          }
          const result = await response.json();
          messageBuffer.delete(jid_local)
          debounceTimers.delete(jid_local)
        } catch (error) {
          console.error(error.message);
          console.log(JSON.stringify(allMessages))
          
          debounceTimers.delete(jid_local)
          debounceTimers.set(jid_local, setTimeout(() => { repeat_timer(jid_local, isfromMe_local)}, DEBOUNCE_MS))
        }
      }

      if (type !== 'notify') return;

        for (const msg of messages) {
            if (!msg.message) return;
            
            const body = msg.message.conversation || msg.message.extendedTextMessage?.text || ""
            const sender = msg.key.remoteJid
            const name = msg.pushName || "waSocket"

            const jid = msg.key.remoteJid.startsWith("62") ? msg.key.remoteJid :  msg.key.remoteJidAlt
            if (!jid) return
            // if (jid.endsWith("@g.us")) return
            if (msg.message.protocolMessage) return;

            const decode = jidDecode(jid);
            const phoneNumber = decode.user.split("@")[0].split("-")[0]
            // console.log(phoneNumber)
            // console.log(msg.message)

            const text =
              msg.message.conversation ||
              msg.message.extendedTextMessage?.text ||
              msg.message.imageMessage?.caption ||
              msg.message.videoMessage?.caption ||
              ""

            const isfromMe = msg.key.fromMe

            if (!messageBuffer.has(msg.key.remoteJid)) {
              messageBuffer.set(msg.key.remoteJid, {'jid': msg.key.remoteJid, 'phoneNumber': phoneNumber, 'name': name, text: [], isfromMe: isfromMe})
            }
            messageBuffer.get(msg.key.remoteJid)['text'].push(text)

            // ===============================
            // 2. Reset timer debounce
            // ===============================
            if (debounceTimers.has(msg.key.remoteJid)) {
              clearTimeout(debounceTimers.get(msg.key.remoteJid))
            }

            debounceTimers.set(msg.key.remoteJid, setTimeout(() => { repeat_timer(msg.key.remoteJid, isfromMe)}, DEBOUNCE_MS))

        }
    })
    
}

// Jalankan Koneksi WhatsApp

function getSocket() {
    if (!waSocket) throw new Error("WhatsApp not ready")
    return waSocket
}

export { connectToWhatsApp, getSocket }
