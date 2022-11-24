import React from 'react';


const Vertical = (props) => {
    return (
        <div className='vertical' id={props.id}>
             <span className="verticalContent">{props.children}</span>
            <span className='verticalLine'></span>
        </div>
    );
};

export default Vertical;