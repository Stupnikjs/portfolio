
import Navlink from '../components/Navlink';



const Navbar = () => {

    return (
        <div className={"navbar"}>
            <Navlink key={1} id={1} to="/about">01. A propos</Navlink>
            <Navlink  key={2} id={2}  to="/experience" >02. Experience</Navlink>
            <Navlink  key={3} id={3}  to="/curriculum">03. Mon CV</Navlink>
            <Navlink key={4} id={4} to="/contact">04. Contact</Navlink>  
        </div>
    );
};

export default Navbar;