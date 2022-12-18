
import Navlink from './Navlink.js';
import styles from "./navbar.module.css"


const cabinet_items = [ 
    {text: "Notre Equipe", link:"/cabinet/equipe"},
     {text: "Nos Valeurs", link: "/cabinet/nosvaleurs"},
     {text: "Méthodologie et honoraires", link: "/cabinet/methodologie"}
    ]

const expertise_items = [
    { text: "Urbanime et aménagement", link:"/expertise/urbanisme"}, 
    { text: "Construction", link:"/expertise/construction"}, 
    { text: "Comande publique", link:"/expertise/commande"}, 
    {text: "Environement", link:"/expertise/environement"}, 
    { text: "Droit public général", link:"/expertise/droitpublic"}, 
]

const Navbar = ({current}) => {
    

    return (
        <header className={styles.navbar}>
            <Navlink current={current} key={1} to="/accueil" >Accueil</Navlink>
            <Navlink current={current} key={2} to="/about" >A Propos</Navlink>
            <Navlink current={current} key={3} to="/experiences" >Experiences</Navlink>     
            <Navlink current={current} key={3} to="/contact" >Contact</Navlink>     
        </header>
    );
};

export default Navbar;