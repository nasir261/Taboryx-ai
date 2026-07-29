import SwiftUI

private struct MemoryCard: Identifiable {
    let id: Int
    let emoji: String
    var isFlipped = false
    var isMatched = false
}

struct MemoryMatchView: View {
    private let emojis = ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼"]
    private let columns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 4)

    @State private var cards: [MemoryCard] = []
    @State private var firstIndex: Int? = nil
    @State private var secondIndex: Int? = nil
    @State private var score = 0
    @State private var moves = 0
    @State private var isChecking = false
    @State private var won = false

    var body: some View {
        ZStack {
            Color(red: 0.08, green: 0.0, blue: 0.18).ignoresSafeArea()
            VStack(spacing: 16) {
                Text("🃏 Memory Match")
                    .font(.system(size: 22, weight: .bold, design: .monospaced))
                    .foregroundColor(.yellow)

                HStack {
                    Label("\(score)/8 pairs", systemImage: "star.fill")
                        .font(.system(size: 17, weight: .bold, design: .monospaced))
                        .foregroundColor(.yellow)
                    Spacer()
                    Label("\(moves) moves", systemImage: "hand.tap")
                        .font(.system(size: 17, weight: .bold, design: .monospaced))
                        .foregroundColor(.white)
                }
                .padding(.horizontal)

                LazyVGrid(columns: columns, spacing: 10) {
                    ForEach(cards) { card in
                        CardTile(card: card)
                            .onTapGesture { flipCard(card) }
                    }
                }
                .padding(.horizontal)

                if won {
                    winBanner
                }
                Spacer()
            }
            .padding(.top)
        }
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { setupGame() }
    }

    // MARK: – Win banner

    private var winBanner: some View {
        VStack(spacing: 12) {
            Text("🎉 You Win!")
                .font(.system(size: 30, weight: .bold, design: .monospaced))
                .foregroundColor(.yellow)
            Text("\(moves) moves")
                .font(.system(size: 18, design: .monospaced))
                .foregroundColor(.white)
            Button("Play Again 🔄") { setupGame() }
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(.black)
                .padding(.horizontal, 28)
                .padding(.vertical, 12)
                .background(Color.yellow)
                .cornerRadius(14)
        }
        .padding(.top, 8)
    }

    // MARK: – Game logic

    private func setupGame() {
        let shuffled = (emojis + emojis).shuffled()
        cards = shuffled.enumerated().map { MemoryCard(id: $0.offset, emoji: $0.element) }
        firstIndex = nil
        secondIndex = nil
        score = 0
        moves = 0
        won = false
    }

    private func flipCard(_ card: MemoryCard) {
        guard !isChecking, !card.isFlipped, !card.isMatched else { return }
        cards[card.id].isFlipped = true

        if firstIndex == nil {
            firstIndex = card.id
        } else if secondIndex == nil {
            secondIndex = card.id
            moves += 1
            checkForMatch()
        }
    }

    private func checkForMatch() {
        guard let a = firstIndex, let b = secondIndex else { return }
        isChecking = true

        if cards[a].emoji == cards[b].emoji {
            cards[a].isMatched = true
            cards[b].isMatched = true
            score += 1
            firstIndex = nil
            secondIndex = nil
            isChecking = false
            if score == emojis.count { won = true }
        } else {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.9) {
                cards[a].isFlipped = false
                cards[b].isFlipped = false
                firstIndex = nil
                secondIndex = nil
                isChecking = false
            }
        }
    }
}

// MARK: – Card tile view

private struct CardTile: View {
    let card: MemoryCard

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 10)
                .fill(card.isMatched ? Color.green.opacity(0.55)
                      : card.isFlipped ? Color.white
                      : Color.purple)
                .frame(height: 76)

            if card.isFlipped || card.isMatched {
                Text(card.emoji)
                    .font(.system(size: 38))
            } else {
                Text("?")
                    .font(.system(size: 30, weight: .heavy, design: .monospaced))
                    .foregroundColor(.white.opacity(0.8))
            }
        }
        .animation(.easeInOut(duration: 0.25), value: card.isFlipped)
        .animation(.easeInOut(duration: 0.25), value: card.isMatched)
    }
}

#Preview {
    MemoryMatchView()
}
