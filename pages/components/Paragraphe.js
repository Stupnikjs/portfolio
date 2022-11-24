import React from 'react';

const Paragraphe = (props) => {
    return (
        <div className='paragraphe intro'>
            {props.children}
        </div>
    );
};

export default Paragraphe;