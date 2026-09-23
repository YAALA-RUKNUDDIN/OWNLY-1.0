allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

// Raise any Android subproject that pins an older compileSdk than its
// dependencies require (file_picker compiles at 34 while
// flutter_plugin_android_lifecycle needs 36+). Registered BEFORE the
// evaluationDependsOn block below so this callback is first in each
// subproject's afterEvaluate queue — AGP locks compileSdk once it reads it,
// which happens later. Failures are logged, never fatal.
subprojects {
    afterEvaluate {
        try {
            val androidExt = extensions.findByName("android") ?: return@afterEvaluate
            val cls = androidExt.javaClass
            fun currentSdk(): Int? =
                listOf("getCompileSdk", "getCompileSdkVersion")
                    .mapNotNull { n -> cls.methods.firstOrNull { it.name == n && it.parameterCount == 0 } }
                    .firstNotNullOfOrNull { m -> (m.invoke(androidExt) as? Int) }
            val current = currentSdk() ?: return@afterEvaluate
            if (current >= 36) return@afterEvaluate
            val setter = cls.methods.firstOrNull { m ->
                m.parameterCount == 1 &&
                    m.parameterTypes[0] == Int::class.javaPrimitiveType &&
                    m.name in setOf("setCompileSdk", "setCompileSdkVersion", "compileSdkVersion")
            }
            if (setter != null) {
                setter.invoke(androidExt, 36)
                logger.info("Raised ${project.path} compileSdk $current -> 36")
            }
        } catch (t: Throwable) {
            logger.warn("Could not raise compileSdk for ${project.path}: ${t.message}")
        }
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
