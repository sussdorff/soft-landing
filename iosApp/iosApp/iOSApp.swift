import SwiftUI
import ComposeApp

class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        return true
    }
}

@main
struct iOSApp: App {

    init() {
        KoinHelperKt.startKoinIos()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
