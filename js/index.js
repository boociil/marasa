// const { makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion } = require("baileys")
import { makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion } from 'baileys';
import pino from 'pino';
import chalk from 'chalk';
import readline from 'node:readline';
import {resolve} from 'path';
import {version} from 'os';

import dotenv from 'dotenv';
dotenv.config();

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

const DEBOUNCE_MS = 10_000

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState('./waSocketSesi')
  
  // Versi Terbaru
  const { version, isLatest } = await fetchLatestBaileysVersion()
  console.log(`Using WA v${version.join('.')}, isLatest: ${isLatest}`)

  const waSocket = makeWASocket({
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
        if(!isfromMe_local){
          return
        }
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

          result.forEach(element => {
              sendMessage(jid_local, element)
          });

          messageBuffer.delete(jid_local)
          debounceTimers.delete(jid_local)
        } catch (error) {
          console.error(error.message);
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

            const jid = msg.key.remoteJid
            // if (!jid.endsWith("@s.whatsapp.net")) return
            const phoneNumber = jid.split("@")[0].split("-")[0]


            const text =
              msg.message.conversation ||
              msg.message.extendedTextMessage?.text ||
              msg.message.imageMessage?.caption ||
              msg.message.videoMessage?.caption ||
              ""

            const isfromMe = msg.key.fromMe

            if (!messageBuffer.has(jid)) {
              messageBuffer.set(jid, {'jid': jid, 'phoneNumber': phoneNumber, 'name': name, text: [], isfromMe: isfromMe})
            }
            messageBuffer.get(jid)['text'].push(text)

            // ===============================
            // 2. Reset timer debounce
            // ===============================
            if (debounceTimers.has(jid)) {
              clearTimeout(debounceTimers.get(jid))
            }

            debounceTimers.set(jid, setTimeout(() => { repeat_timer(jid, isfromMe)}, DEBOUNCE_MS))

        }
    })
    
}

// Jalankan Koneksi WhatsApp
connectToWhatsApp()
