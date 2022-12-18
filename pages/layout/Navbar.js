
import Navlink from './Navlink';
import styles from "./navbar.module.css"




const Navbar = ({current}) => {
    

    return (
        <header className={styles.navbar}>
            <Navlink current={current} key={1} to="/" >Accueil</Navlink>
            <Navlink current={current} key={2} to="/about" >A Propos</Navlink>
            <Navlink current={current} key={3} to="/experience" >Experiences</Navlink>     
            <Navlink current={current} key={3} to="/curriculum" >Curriculum</Navlink>     
            <Navlink current={current} key={3} to="/contact" >Contact</Navlink>     
        </header>
    );
};

export default Navbar;