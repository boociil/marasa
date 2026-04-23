const express = require("express")
const { connectToWhatsApp, getSocket } = require("./waService")
const multer  = require('multer')


const upload = multer({ storage: multer.memoryStorage() })
const app = express()
app.use(express.json())

// start WA saat server boot
connectToWhatsApp()

// endpoint kirim pesan
app.post("/send-message", upload.single("image"), async (req, res) => {
    try {
        const { jid, answers } = req.body

        if (!jid || !answers)
            return res.status(400).json({ error: "jid & answers required" })

        const sock = getSocket()

        const file = req.image
        let payload

        // jika ada file image upload
        if (file) {
            payload = {
                image: file.buffer, // <- buffer dari multer
                mimetype: file.mimetype,
                caption: message || ""
            }
        }else if (message) {
            payload = { text: message }
        }
        

        await sock.sendMessage(jid, payload)

        res.json({ status: "Message sent ✅" })
    } catch (err) {
        console.error(err)
        res.status(500).json({ error: err.message })
    }
})

app.listen(3000, () => console.log("API running on port 3000"))