import re

login_file = "/home/eliezer/Escritorio/Dominus-Order-Manager/app/src/main/java/com/dominus/ordermanager/LoginActivity.kt"
with open(login_file, "r") as f:
    login_code = f.read()

# Fix 1 & 2: JSON Injection and Memory Leak
old_login_func = """    private fun performLogin(username: String, password: String): Boolean {
        val client = OkHttpClient()
        val mediaType = "application/json; charset=utf-8".toMediaType()
        // Simple JSON payload construction (In a real app, use Gson/Moshi)
        val json = \"\"\"
            {
                "email": "$username",
                "password": "$password"
            }
        \"\"\".trimIndent()

        val requestBody = json.toRequestBody(mediaType)
        // Hardcoded to point to the local backend using emulator loopback address for testing
        // Change to your actual backend IP or dominuslabs.online
        val request = Request.Builder()
            .url("http://10.0.2.2:8000/api/v1/auth/login")
            .post(requestBody)
            .build()

        return try {
            val response = client.newCall(request).execute()
            response.isSuccessful
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }"""

new_login_func = """    private val client = OkHttpClient()
    private fun performLogin(username: String, password: String): Boolean {
        val formBody = okhttp3.FormBody.Builder()
            .add("username", username)
            .add("password", password)
            .build()
        
        val request = Request.Builder()
            .url("https://dominuslabs.online/api/v1/auth/login")
            .post(formBody)
            .build()

        return try {
            client.newCall(request).execute().use { response ->
                response.isSuccessful
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }"""
login_code = login_code.replace(old_login_func, new_login_func)
with open(login_file, "w") as f:
    f.write(login_code)


fcm_file = "/home/eliezer/Escritorio/Dominus-Order-Manager/app/src/main/java/com/dominus/ordermanager/MyFirebaseMessagingService.kt"
with open(fcm_file, "r") as f:
    fcm_code = f.read()

# Fix 3: FLAG_MUTABLE -> FLAG_IMMUTABLE
fcm_code = fcm_code.replace("PendingIntent.FLAG_MUTABLE", "PendingIntent.FLAG_IMMUTABLE")
with open(fcm_file, "w") as f:
    fcm_code = fcm_code.replace("import android.app.PendingIntent", "import android.app.PendingIntent\nimport android.os.Build")
    f.write(fcm_code)


alert_file = "/home/eliezer/Escritorio/Dominus-Order-Manager/app/src/main/java/com/dominus/ordermanager/OrderAlertActivity.kt"
with open(alert_file, "r") as f:
    alert_code = f.read()

# Fix 4: TTS delay
alert_code = alert_code.replace("delay(5000)", "delay(15000)")
with open(alert_file, "w") as f:
    f.write(alert_code)

print("Fixed Android PoC!")
