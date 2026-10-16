
import './Home.css'

const Home = () => {
  return (
    <div className="home">
      <section className="hero">
        <h1>RL Chess Assistant</h1>
        <p className="hero-sub">
          Reinforcement Learning Powered Chess Engine
        </p>
      </section>

      <section className="about">
        <div className="about-intro">
          <span className="about-eyebrow">1. About the Engine</span>
          <h2>Built to explain, not just evaluate</h2>
          <p>
            Most chess engines are built to find the best move. This one is
            built to help you find your best game. A custom reinforcement
            learning engine — trained through self-play
             — pairs with a natural-language layer that
            gives strategic lessons you can actually learn from.
            
          </p>
        </div>

        <div className="about-moves">
          <div className="move-row">
            <span className="move-notation"></span>
            <div className="move-text">
              <h3>Built from scratch</h3>
              <p>Custom RL engine and NNUE evaluation network</p>
            </div>
          </div>
          <div className="move-row">
            <span className="move-notation"></span>
            <div className="move-text">
              <h3>Explanation over evaluation</h3>
              <p>Numbers matter, but understanding what actually improves your play.</p>
            </div>
          </div>
          <div className="move-row">
            <span className="move-notation"></span>
            <div className="move-text">
              <h3>Personalization that learns</h3>
              <p>Tracks your recurring weaknesses over time and adapts its coaching accordingly.</p>
            </div>
          </div>
          <div className="move-row">
            <span className="move-notation"></span>
            <div className="move-text">
              <h3>Built for real hardware</h3>
              <p>Designed to run efficiently, without needing a server farm.</p>
            </div>
          </div>
        </div>

        <div className="about-philosophy">
          <p>
            Chess engines have always been generous with information and stingy with insight. It will tell you the eval dropped by two
            pawns, but not what that meant for your king safety three moves
            later. This assistant exists to close that gap — treating your
            growth as the actual goal, not just raw engine strength.
          </p>
        </div>
      </section>
    </div>
  );
};

export default Home;