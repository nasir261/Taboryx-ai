import SwiftUI

struct HomeView: View {
    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                VStack(spacing: 22) {
                    Text("🎮 90s Kids Games")
                        .font(.system(size: 36, weight: .bold, design: .monospaced))
                        .foregroundColor(.yellow)
                        .padding(.top, 14)

                    GameMenuButton(title: "🐍  Snake",        color: .green,  destination: AnyView(SnakeGameView()))
                    GameMenuButton(title: "🃏  Memory Match", color: .blue,   destination: AnyView(MemoryMatchView()))
                    GameMenuButton(title: "🔨  Whack-a-Mole", color: .orange, destination: AnyView(WhackAMoleView()))
                    GameMenuButton(title: "🏓  Pong",         color: .purple, destination: AnyView(PongView()))
                    GameMenuButton(title: "🧱  Breakout",     color: .red,    destination: AnyView(BreakoutView()))
                }
                .padding(.horizontal, 20)
            }
            .navigationBarHidden(true)
        }
    }
}

private struct GameMenuButton: View {
    let title: String
    let color: Color
    let destination: AnyView

    var body: some View {
        NavigationLink(destination: destination) {
            Text(title)
                .font(.system(size: 32, weight: .bold, design: .monospaced))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 28)
                .background(color)
                .cornerRadius(22)
                .shadow(color: color.opacity(0.6), radius: 10, y: 5)
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    HomeView()
}
